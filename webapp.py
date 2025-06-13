from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
import aiosqlite
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = FastAPI()

@app.get("/webapp")
async def webapp():
    logging.info("Запрос к веб-приложению")
    return await FileResponse("webapp.html")

@app.get("/api/part/{chat_id}")
async def get_part(chat_id: int):
    async with aiosqlite.connect('bot.db') as db:
        try:
            cursor = await db.execute('SELECT current_book_id, current_part FROM users WHERE chat_id = ?', (chat_id,))
            row = await cursor.fetchone()
            if row:
                book_id, current_part = row
                cursor = await db.execute('SELECT text FROM parts WHERE book_id = ? AND part_number = ?', (book_id, current_part))
                part_row = await cursor.fetchone()
                if part_row:
                    logging.info(f"Отправлен фрагмент {current_part} книги {book_id} для {chat_id}")
                    return {"status": "OK", "text": part_row[0]}
                return {"status": "error", "text": "Нет текущего фрагмента"}
            return {"status": "error", "text": "Книга не выбрана"}
        except Exception as e:
            logging.error(f"Ошибка при получении фрагмента для {chat_id}: {e}")
            return {"status": "error", "text": "Ошибка сервера"}

@app.post("/api/next/{chat_id}")
async def next_part(chat_id: int):
    async with aiosqlite.connect('bot.db') as db:
        try:
            cursor = await db.execute('SELECT current_book_id, current_part FROM users WHERE chat_id = ?', (chat_id,))
            row = await cursor.fetchone()
            if row:
                book_id, current_part = row
                next_part = current_part + 1
                cursor = await db.execute('SELECT part_id FROM parts WHERE book_id = ? AND part_number = ?', (book_id, next_part))
                if await cursor.fetchone():
                    await db.execute('UPDATE users SET current_part = ? WHERE chat_id = ?', (next_part, chat_id))
                    await db.commit()
                    logging.info(f"Пользователь {chat_id} перешёл к следующему фрагменту {next_part}")
                    return {"status": "success"}
                return {"status": "error", "message": "Это последний фрагмент"}
            return {"status": "error", "message": "Книга не выбрана"}
        except Exception as e:
            logging.error(f"Ошибка при переходе к следующему фрагменту для {chat_id}: {e}")
            return {"status": "error", "message": "Ошибка сервера"}

@app.post("/api/prev/{chat_id}")
async def prev_part(chat_id: int):
    async with aiosqlite.connect('bot.db') as db:
        try:
            cursor = await db.execute('SELECT current_book_id, current_part FROM users WHERE chat_id = ?', (chat_id,))
            row = await cursor.fetchone()
            if row:
                book_id, current_part = row
                prev_part = current_part - 1
                if prev_part >= 1:
                    await db.execute('UPDATE users SET current_part = ? WHERE chat_id = ?', (prev_part, chat_id))
                    await db.commit()
                    logging.info(f"Пользователь {chat_id} перешёл к предыдущему фрагменту {prev_part}")
                    return {"status": "success"}
                return {"status": "error", "message": "Это первый фрагмент"}
            return {"status": "error", "message": "Книга не выбрана"}
        except Exception as e:
            logging.error(f"Ошибка при переходе к предыдущему фрагменту для {chat_id}: {e}")
            return {"status": "error", "message": "Ошибка сервера"}

@app.get("/api/books/{chat_id}")
async def get_books(chat_id: int):
    async with aiosqlite.connect('bot.db') as db:
        try:
            cursor = await db.execute('SELECT book_id, title FROM books WHERE user_id = ?', (chat_id,))
            books = await cursor.fetchall()
            logging.info(f"Список книг отправлен для {chat_id}")
            return [{"book_id": book_id, "title": title} for book_id, title in books]
        except Exception as e:
            logging.error(f"Ошибка при получении списка книг для {chat_id}: {e}")
            return {"status": "error", "message": "Ошибка сервера"}

@app.post("/api/select_book/{chat_id}/{book_id}")
async def select_book(chat_id: int, book_id: int):
    async with aiosqlite.connect('bot.db') as db:
        try:
            cursor = await db.execute('SELECT book_id FROM books WHERE book_id = ? AND user_id = ?', (book_id, chat_id))
            if await cursor.fetchone():
                await db.execute('UPDATE users SET current_book_id = ?, current_part = 1 WHERE chat_id = ?', (book_id, chat_id))
                await db.commit()
                logging.info(f"Пользователь {chat_id} выбрал книгу {book_id}")
                return {"status": "success"}
            return {"status": "error", "message": "Книга не найдена"}
        except Exception as e:
            logging.error(f"Ошибка при выборе книги {book_id} для {chat_id}: {e}")
            return {"status": "error", "message": "Ошибка сервера"}