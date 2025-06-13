import aiosqlite
import logging

async def init_db():
    async with aiosqlite.connect('bot.db') as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            current_book_id INTEGER,
            current_part INTEGER,
            schedule_start_time TEXT,
            schedule_end_time TEXT,
            schedule_interval INTEGER,
            preferred_voice TEXT
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS parts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id INTEGER,
            part_number INTEGER,
            text TEXT
        )''')
        await db.commit()
    logging.info("База данных инициализирована")

async def add_book(user_id, title):
    async with aiosqlite.connect('bot.db') as db:
        await db.execute('INSERT INTO books (user_id, title) VALUES (?, ?)', (user_id, title))
        await db.commit()
        cursor = await db.execute('SELECT last_insert_rowid()')
        book_id = (await cursor.fetchone())[0]
        logging.info(f"Добавлена книга {title} для user_id {user_id}, book_id: {book_id}")
        return book_id

async def add_part(book_id, part_number, text):
    async with aiosqlite.connect('bot.db') as db:
        await db.execute('INSERT INTO parts (book_id, part_number, text) VALUES (?, ?, ?)', (book_id, part_number, text))
        await db.commit()
        logging.info(f"Добавлена часть {part_number} для книги {book_id}")

async def get_books(user_id):
    async with aiosqlite.connect('bot.db') as db:
        cursor = await db.execute('SELECT id, title FROM books WHERE user_id = ?', (user_id,))
        books = await cursor.fetchall()
        logging.info(f"Получен список книг для user_id {user_id}: {len(books)} книг")
        return books

async def get_part_text(book_id, part_number):
    async with aiosqlite.connect('bot.db') as db:
        cursor = await db.execute('SELECT text FROM parts WHERE book_id = ? AND part_number = ?', (book_id, part_number))
        row = await cursor.fetchone()
        logging.info(f"Запрошен текст части {part_number} для книги {book_id}: {'найден' if row else 'не найден'}")
        return row[0] if row else None

async def get_total_parts(book_id):
    async with aiosqlite.connect('bot.db') as db:
        cursor = await db.execute('SELECT COUNT(*) FROM parts WHERE book_id = ?', (book_id,))
        count = (await cursor.fetchone())[0]
        logging.info(f"Общее количество частей для книги {book_id}: {count}")
        return count

async def get_user_data(chat_id):
    async with aiosqlite.connect('bot.db') as db:
        cursor = await db.execute('SELECT current_book_id, current_part, preferred_voice FROM users WHERE chat_id = ?', (chat_id,))
        row = await cursor.fetchone()
        if row:
            logging.info(f"Данные пользователя {chat_id}: book_id={row[0]}, part={row[1]}, voice={row[2]}")
            return {"current_book_id": row[0], "current_part": row[1], "preferred_voice": row[2]}
        logging.info(f"Данные пользователя {chat_id} не найдены")
        return None

async def update_user_data(chat_id, data):
    async with aiosqlite.connect('bot.db') as db:
        cursor = await db.execute('SELECT 1 FROM users WHERE chat_id = ?', (chat_id,))
        exists = await cursor.fetchone()
        if exists:
            for key, value in data.items():
                query = f'UPDATE users SET {key} = ? WHERE chat_id = ?'
                await db.execute(query, (value, chat_id))
        else:
            columns = ', '.join(['chat_id'] + list(data.keys()))
            placeholders = ', '.join('?' * (len(data) + 1))
            values = (chat_id, *data.values())
            query = f'INSERT INTO users ({columns}) VALUES ({placeholders})'
            await db.execute(query, values)
        await db.commit()
        logging.info(f"Обновлены данные пользователя {chat_id}: {data}")

async def get_books_count(user_id):
    async with aiosqlite.connect('bot.db') as db:
        cursor = await db.execute('SELECT COUNT(*) FROM books WHERE user_id = ?', (user_id,))
        count = (await cursor.fetchone())[0]
        logging.info(f"Количество книг для user_id {user_id}: {count}")
        return count

async def delete_book(book_id, user_id):
    async with aiosqlite.connect('bot.db') as db:
        await db.execute('DELETE FROM books WHERE id = ? AND user_id = ?', (book_id, user_id))
        await db.execute('DELETE FROM parts WHERE book_id = ?', (book_id,))
        await db.commit()
        logging.info(f"Удалена книга {book_id} для user_id {user_id}")