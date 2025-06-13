from aiogram import types

def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Назад"), types.KeyboardButton(text="Вперед")],
            [types.KeyboardButton(text="Выбор книги"), types.KeyboardButton(text="Расписание")],
            [types.KeyboardButton(text="Открыть веб-приложение"), types.KeyboardButton(text="Управление загрузкой")],
            [types.KeyboardButton(text="Читать сейчас")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_manage_upload_keyboard():
    keyboard = types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="Загрузить текст")],
            [types.KeyboardButton(text="Удалить книгу")],
            [types.KeyboardButton(text="Назад")]
        ],
        resize_keyboard=True
    )
    return keyboard

def split_text_into_parts(text, max_chars=4000):
    parts = []
    while len(text) > max_chars:
        split_index = text.rfind('\n', 0, max_chars)
        if split_index == -1 or split_index == 0:
            split_index = max_chars
        parts.append(text[:split_index].strip())
        text = text[split_index:].strip()
    if text:
        parts.append(text)
    return parts