import logging
import asyncio
import aiohttp
from io import BytesIO
import pdfplumber
import ebooklib
from ebooklib import epub
from docx import Document
import requests
from bs4 import BeautifulSoup
import trafilatura
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from config import API_TOKEN
from datetime import datetime, timedelta
import base64
import io
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, BufferedInputFile
from aiogram.fsm.context import FSMContext
import chardet
from keyboard_handlers import register_keyboard_handlers
from database import init_db, add_book, add_part, get_books, update_user_data, get_books_count, delete_book, get_user_data, get_part_text, get_total_parts
from ai_utils import generate_audio, format_text_with_ai
from utils import get_main_keyboard, split_text_into_parts, get_manage_upload_keyboard
from states import ScheduleForm, set_schedule

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('api_log.txt')
    ]
)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Настройка FastAPI для веб-приложения
app = FastAPI()

@app.get("/webapp")
async def webapp():
    logging.info("Запрос к веб-приложению")
    return FileResponse("webapp.html")

# Доступные голоса для Pollinations.ai
VOICES = ["Alloy", "Echo", "Fable", "Nova", "Onyx", "Shimmer", "Coral", "Verse", "Ballad", "Ash", "Sage", "Amuch", "Dan"]

# Функции извлечения текста из файлов
def extract_text_from_pdf(file_bytes):
    text = ''
    with pdfplumber.open(BytesIO(file_bytes.getvalue())) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(layout=True) or ''
            text += page_text + '\n\n'
    return text.strip()

def extract_text_from_epub(file_bytes):
    book = epub.read_epub(BytesIO(file_bytes.getvalue()))
    text = ''
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), 'html.parser')
        for p in soup.find_all(['p', 'div']):
            paragraph = p.get_text().strip()
            if paragraph:
                text += paragraph + '\n\n'
    return text.strip()

def extract_text_from_txt(file_bytes):
    raw_data = file_bytes.getvalue()
    detected = chardet.detect(raw_data)
    encoding = detected['encoding'] or 'utf-8'
    try:
        return raw_data.decode(encoding).strip()
    except UnicodeDecodeError:
        logging.error(f"Не удалось декодировать файл с кодировкой {encoding}")
        return None

def extract_text_from_html(file_bytes):
    soup = BeautifulSoup(file_bytes.getvalue(), 'html.parser')
    text = ''
    for p in soup.find_all(['p', 'div', 'article']):
        paragraph = p.get_text().strip()
        if paragraph:
            text += paragraph + '\n\n'
    return text.strip()

def extract_text_from_docx(file_bytes):
    doc = Document(BytesIO(file_bytes.getvalue()))
    text = ''
    for para in doc.paragraphs:
        if para.text.strip():
            text += para.text + '\n\n'
    return text.strip()

# Запуск бота
async def on_startup():
    await init_db()
    logging.info("Бот запущен")

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Добро пожаловать в бот для чтения! Загрузите файл книги или отправьте ссылку, чтобы начать.", reply_markup=get_main_keyboard())
    await update_user_data(message.chat.id, {})
    logging.info(f"Пользователь {message.chat.id} запустил бота")

# Обработка загрузки документов
@dp.message(lambda message: message.document is not None)
async def handle_document(message: types.Message):
    books_count = await get_books_count(message.chat.id)
    if books_count >= 5:
        await message.answer("У вас уже есть 5 книг. Пожалуйста, удалите одну из них, чтобы добавить новую.", reply_markup=get_main_keyboard())
        return
    document = message.document
    file_info = await bot.get_file(document.file_id)
    file_bytes = await bot.download_file(file_info.file_path)
    file_name = document.file_name.lower()
    
    if file_name.endswith('.pdf'):
        text = extract_text_from_pdf(file_bytes)
    elif file_name.endswith('.epub'):
        text = extract_text_from_epub(file_bytes)
    elif file_name.endswith('.txt'):
        text = extract_text_from_txt(file_bytes)
        if text is None:
            await message.answer("Не удалось прочитать текстовый файл. Проверьте кодировку.", reply_markup=get_main_keyboard())
            return
    elif file_name.endswith('.html'):
        text = extract_text_from_html(file_bytes)
    elif file_name.endswith('.docx'):
        text = extract_text_from_docx(file_bytes)
    else:
        await message.answer("Неподдерживаемый формат файла. Поддерживаются: PDF, EPUB, TXT, HTML, DOCX.", reply_markup=get_main_keyboard())
        logging.warning(f"Пользователь {message.chat.id} отправил неподдерживаемый файл: {file_name}")
        return
    
    parts = split_text_into_parts(text)
    logging.info(f"Книга {file_name} разделена на {len(parts)} частей")
    book_id = await add_book(message.chat.id, file_name)
    for i, part in enumerate(parts, 1):
        await add_part(book_id, i, part)
    await update_user_data(message.chat.id, {"current_book_id": book_id, "current_part": 1})
    await message.answer("Книга обработана и выбрана. Используйте кнопки 'Вперед' или 'Назад' для чтения или настройте расписание с помощью /schedule.", reply_markup=get_main_keyboard())
    logging.info(f"Пользователь {message.chat.id} загрузил и выбрал книгу: {file_name}")

# Обработка ссылок
@dp.message(lambda message: message.text and message.text.startswith('http'))
async def handle_link(message: types.Message):
    books_count = await get_books_count(message.chat.id)
    if books_count >= 5:
        await message.answer("У вас уже есть 5 книг. Пожалуйста, удалите одну из них, чтобы добавить новую.", reply_markup=get_main_keyboard())
        return
    url = message.text
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            html = await response.text()
    text = trafilatura.extract(html)
    if text:
        formatted_text = await format_text_with_ai(text, message.chat.id, bot)
        parts = split_text_into_parts(formatted_text)
        logging.info(f"Ссылка {url} разделена на {len(parts)} частей")
        book_id = await add_book(message.chat.id, url)
        for i, part in enumerate(parts, 1):
            await add_part(book_id, i, part)
        await update_user_data(message.chat.id, {"current_book_id": book_id, "current_part": 1})
        await message.answer("Ссылка обработана и книга выбрана. Используйте кнопки 'Вперед' или 'Назад' для чтения или настройте расписание с помощью /schedule.", reply_markup=get_main_keyboard())
        logging.info(f"Пользователь {message.chat.id} обработал и выбрал ссылку: {url}")
    else:
        await message.answer("Не удалось извлечь текст по ссылке.", reply_markup=get_main_keyboard())
        logging.warning(f"Не удалось извлечь текст по ссылке: {url}")

# Команда /schedule
@dp.message(Command("schedule"))
async def cmd_schedule(message: types.Message, state: FSMContext):
    await message.answer("Введите время начала отправки фрагментов (HH:MM):", reply_markup=get_main_keyboard())
    await state.set_state(ScheduleForm.start_time)
    logging.info(f"Пользователь {message.chat.id} начал настройку расписания")

@dp.message(StateFilter(ScheduleForm.start_time))
async def process_start_time(message: types.Message, state: FSMContext):
    start_time = message.text
    try:
        hour, minute = map(int, start_time.split(':'))
        if 0 <= hour < 24 and 0 <= minute < 60:
            await state.update_data(start_time=start_time)
            await message.answer("Введите время окончания отправки фрагментов (HH:MM):", reply_markup=get_main_keyboard())
            await state.set_state(ScheduleForm.end_time)
        else:
            await message.answer("Неверное время. Используйте формат HH:MM.", reply_markup=get_main_keyboard())
    except ValueError:
        await message.answer("Неверный формат времени. Используйте HH:MM.", reply_markup=get_main_keyboard())

@dp.message(StateFilter(ScheduleForm.end_time))
async def process_end_time(message: types.Message, state: FSMContext):
    end_time = message.text
    try:
        hour, minute = map(int, end_time.split(':'))
        if 0 <= hour < 24 and 0 <= minute < 60:
            await state.update_data(end_time=end_time)
            await message.answer("Введите периодичность отправки фрагментов (в часах, например, 2):", reply_markup=get_main_keyboard())
            await state.set_state(ScheduleForm.interval)
        else:
            await message.answer("Неверное время. Используйте формат HH:MM.", reply_markup=get_main_keyboard())
    except ValueError:
        await message.answer("Неверный формат времени. Используйте HH:MM.", reply_markup=get_main_keyboard())

@dp.message(StateFilter(ScheduleForm.interval))
async def process_interval(message: types.Message, state: FSMContext):
    interval = message.text
    try:
        interval = int(interval)
        if interval > 0:
            data = await state.get_data()
            start_time = data['start_time']
            end_time = data['end_time']
            await set_schedule(message.chat.id, start_time, end_time, interval, bot, send_daily_part)
            await message.answer(f"Расписание установлено: фрагменты будут отправляться с {start_time} до {end_time} каждые {interval} часов.", reply_markup=get_main_keyboard())
            await state.clear()
            logging.info(f"Пользователь {message.chat.id} установил расписание")
        else:
            await message.answer("Периодичность должна быть больше 0.", reply_markup=get_main_keyboard())
    except ValueError:
        await message.answer("Неверный формат. Введите число (в часах).", reply_markup=get_main_keyboard())

# Команда /selectbook
@dp.message(Command("selectbook"))
async def cmd_selectbook(message: types.Message):
    books = await get_books(message.chat.id)
    if books:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=title, callback_data=f"book_{book_id}")] for book_id, title in books]
        )
        await message.answer("Выберите книгу для чтения:", reply_markup=keyboard)
    else:
        await message.answer("У вас нет загруженных книг. Загрузите книгу с помощью команды 'Загрузить текст'.", reply_markup=get_main_keyboard())
    logging.info(f"Пользователь {message.chat.id} запросил выбор книги")

@dp.callback_query(lambda c: c.data.startswith('book_'))
async def process_book_choice(callback_query: types.CallbackQuery):
    book_id = int(callback_query.data.split('_')[1])
    chat_id = callback_query.from_user.id
    await update_user_data(chat_id, {"current_book_id": book_id, "current_part": 1})
    await callback_query.message.answer("Книга выбрана. Используйте кнопки 'Вперед' или 'Назад' для чтения.", reply_markup=get_main_keyboard())
    await callback_query.answer()

# Команда /deletebook
@dp.message(Command("deletebook"))
async def cmd_deletebook(message: types.Message):
    books = await get_books(message.chat.id)
    if books:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text=title, callback_data=f"delete_{book_id}")] for book_id, title in books]
        )
        await message.answer("Выберите книгу для удаления:", reply_markup=keyboard)
    else:
        await message.answer("У вас нет загруженных книг.", reply_markup=get_main_keyboard())

@dp.callback_query(lambda c: c.data.startswith('delete_'))
async def process_delete_book(callback_query: types.CallbackQuery):
    book_id = int(callback_query.data.split('_')[1])
    chat_id = callback_query.from_user.id
    await delete_book(book_id, chat_id)
    await callback_query.message.answer("Книга удалена.", reply_markup=get_main_keyboard())
    await callback_query.answer()

# Команда /webapp
@dp.message(Command("webapp"))
async def cmd_webapp(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="Открыть веб-приложение", web_app=types.WebAppInfo(url="https://myreading.hhos.ru/webapp"))]]
    )
    await message.answer("Нажмите, чтобы открыть веб-приложение:", reply_markup=keyboard)
    logging.info(f"Пользователь {message.chat.id} запросил открытие веб-приложения")

# Команда /setvoice
@dp.message(Command("setvoice"))
async def cmd_setvoice(message: types.Message):
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=voice, callback_data=voice)] for voice in VOICES]
    )
    await message.answer("Выберите голос для озвучки:", reply_markup=keyboard)
    logging.info(f"Пользователь {message.chat.id} запросил выбор голоса")

@dp.callback_query(lambda c: c.data in VOICES)
async def process_voice_choice(callback_query: types.CallbackQuery):
    voice = callback_query.data
    await update_user_data(callback_query.from_user.id, {"preferred_voice": voice})
    await callback_query.message.answer(f"Голос установлен: {voice}.", reply_markup=get_main_keyboard())
    await callback_query.answer()
    logging.info(f"Пользователь {callback_query.from_user.id} установил голос {voice}")

# Команда /tts
@dp.message(Command("tts"))
async def cmd_tts(message: types.Message):
    user_data = await get_user_data(message.chat.id)
    if user_data and user_data.get('current_book_id'):
        book_id, current_part, voice = user_data['current_book_id'], user_data['current_part'], user_data.get('preferred_voice')
        if not voice:
            await message.answer("Установите голос с помощью команды /setvoice.", reply_markup=get_main_keyboard())
            return
        text = await get_part_text(book_id, current_part)
        if text:
            audio = await generate_audio(text, voice, chat_id=message.chat.id, bot=bot)
            if audio:
                audio_file = BufferedInputFile(audio, filename="audio.mp3")
                await message.answer_audio(audio_file, reply_markup=get_main_keyboard())
                logging.info(f"Пользователь {message.chat.id} запросил TTS для фрагмента {current_part} книги {book_id}")
            else:
                await message.answer("Не удалось сгенерировать аудио.", reply_markup=get_main_keyboard())
        else:
            await message.answer("Нет текущего фрагмента для чтения.", reply_markup=get_main_keyboard())
    else:
        await message.answer("Книга не выбрана. Используйте /selectbook.", reply_markup=get_main_keyboard())

# Команда /uploadtext
@dp.message(Command("uploadtext"))
async def cmd_upload_text(message: types.Message):
    await message.answer("Отправьте файл книги (PDF, EPUB, TXT, HTML, DOCX) или ссылку на веб-страницу.", reply_markup=get_main_keyboard())
    logging.info(f"Пользователь {message.chat.id} запросил загрузку текста")

# Обработка данных веб-приложения
@dp.message(lambda message: message.web_app_data)
async def handle_webapp_data(message: types.Message):
    if message.web_app_data.data == "tts":
        await cmd_tts(message)

# Обработчик кнопки "Озвучить текст"
@dp.callback_query(lambda c: c.data.startswith('voice_'))
async def voice_text_callback(callback_query: types.CallbackQuery):
    from database import get_part_text, get_user_data
    await callback_query.answer()  # Отвечаем на callback немедленно
    _, book_id, part_number = callback_query.data.split('_')
    book_id = int(book_id)
    part_number = int(part_number)
    chat_id = callback_query.from_user.id
    user_data = await get_user_data(chat_id)
    voice = user_data.get('preferred_voice') or "Alloy" if user_data else "Alloy"
    text = await get_part_text(book_id, part_number)
    logging.info(f"Запрошен текст части {part_number} для книги {book_id}: {'найден' if text else 'не найден'}")
    if text:
        audio_bytes = await generate_audio(text, voice, chat_id=chat_id, bot=bot)
        if audio_bytes:
            audio_file = BufferedInputFile(audio_bytes, filename="audio.mp3")
            await bot.send_audio(chat_id, audio_file)
        else:
            await bot.send_message(chat_id, "Не удалось сгенерировать аудио.")
    else:
        await bot.send_message(chat_id, "Текст не найден.")

# Функция для отправки ежедневного фрагмента
async def send_daily_part(chat_id, bot):
    user_data = await get_user_data(chat_id)
    logging.info(f"User data for {chat_id}: {user_data}")
    if user_data and user_data.get('current_book_id'):
        book_id, current_part = user_data['current_book_id'], user_data['current_part']
        text = await get_part_text(book_id, current_part)
        total_parts = await get_total_parts(book_id)
        if text:
            formatted_text = await format_text_with_ai(text, chat_id, bot)
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=f"Фрагмент {current_part} из {total_parts}", callback_data="dummy")],
                [InlineKeyboardButton(text="Озвучить текст", callback_data=f"voice_{book_id}_{current_part}")]
            ])
            try:
                await bot.send_message(chat_id, formatted_text, reply_markup=keyboard, parse_mode='HTML')
                logging.info(f"Отправлен фрагмент {current_part} книги {book_id} пользователю {chat_id}")
            except Exception as e:
                logging.error(f"Ошибка при отправке сообщения: {e}")
                await bot.send_message(chat_id, "Произошла ошибка при отправке текста.", reply_markup=get_main_keyboard())
            if await get_part_text(book_id, current_part + 1):
                await update_user_data(chat_id, {"current_part": current_part + 1})
            else:
                logging.info(f"Книга {book_id} завершена для пользователя {chat_id}")
                await update_user_data(chat_id, {"current_book_id": None, "current_part": None})
                await bot.send_message(chat_id, "Вы закончили книгу! Выберите новую с помощью /selectbook.", reply_markup=get_main_keyboard())
        else:
            logging.warning(f"Не найдена книга или фрагмент для пользователя {chat_id}")
            await bot.send_message(chat_id, "Книга или фрагмент не найдены.", reply_markup=get_main_keyboard())
    else:
        logging.warning(f"Нет выбранной книги для пользователя {chat_id}")
        await bot.send_message(chat_id, "Книга не выбрана. Используйте /selectbook.", reply_markup=get_main_keyboard())

# Регистрация обработчиков кнопок
register_keyboard_handlers(dp, bot)

# Запуск веб-приложения
async def start_webapp():
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, workers=1)
    server = uvicorn.Server(config)
    await server.serve()

# Основная функция
async def main():
    await on_startup()
    webapp_task = asyncio.create_task(start_webapp())
    await dp.start_polling(bot)
    await webapp_task

if __name__ == '__main__':
    asyncio.run(main())