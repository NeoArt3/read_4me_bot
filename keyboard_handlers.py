from aiogram import types, Dispatcher
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
import logging
from database import get_user_data, get_part_text, get_total_parts, update_user_data
from ai_utils import format_text_with_ai, generate_audio
from utils import get_main_keyboard, get_manage_upload_keyboard
from states import ScheduleForm
import io
from aiogram.types import BufferedInputFile

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Регистрация обработчиков кнопок
def register_keyboard_handlers(dp: Dispatcher, bot):
    @dp.message(lambda message: message.text == "Вперед")
    async def cmd_next_part(message: types.Message):
        """Обработчик кнопки 'Вперед' для перехода к следующему фрагменту книги."""
        chat_id = message.chat.id
        user_data = await get_user_data(chat_id)
        logging.info(f"User data for {chat_id}: {user_data}")
        if user_data and user_data.get('current_book_id'):
            book_id, current_part = user_data['current_book_id'], user_data['current_part']
            total_parts = await get_total_parts(book_id)
            logging.info(f"Книга {book_id}, текущая часть {current_part}/{total_parts}")
            text = await get_part_text(book_id, current_part)
            if text:
                formatted_text = await format_text_with_ai(text, chat_id, bot)
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=f"Фрагмент {current_part} из {total_parts}", callback_data="dummy")],
                    [InlineKeyboardButton(text="Озвучить текст", callback_data=f"voice_{book_id}_{current_part}")]
                ])
                try:
                    await bot.send_message(chat_id, formatted_text, reply_markup=keyboard, parse_mode='HTML')
                    logging.info(f"Пользователь {chat_id} просмотрел фрагмент {current_part}")
                except Exception as e:
                    logging.error(f"Ошибка при отправке сообщения: {e}")
                    await bot.send_message(chat_id, text, reply_markup=keyboard)
                if await get_part_text(book_id, current_part + 1):
                    await update_user_data(chat_id, {"current_part": current_part + 1})
                else:
                    await message.answer(f"Это последний фрагмент книги (всего {total_parts}). Выберите другую книгу с помощью /selectbook.", reply_markup=get_main_keyboard())
            else:
                await message.answer("Нет текущего фрагмента для чтения.", reply_markup=get_main_keyboard())
        else:
            await message.answer("Книга не выбрана. Используйте /selectbook.", reply_markup=get_main_keyboard())

    @dp.message(lambda message: message.text == "Назад")
    async def cmd_prev_part(message: types.Message):
        """Обработчик кнопки 'Назад' для перехода к предыдущему фрагменту книги."""
        chat_id = message.chat.id
        user_data = await get_user_data(chat_id)
        logging.info(f"Нажата кнопка 'Назад' для {chat_id}, user_data: {user_data}")
        if user_data and user_data.get('current_book_id'):
            book_id, current_part = user_data['current_book_id'], user_data['current_part']
            prev_part = current_part - 1
            total_parts = await get_total_parts(book_id)
            logging.info(f"Книга {book_id}, текущая часть {current_part}/{total_parts}")
            if prev_part >= 1:
                text = await get_part_text(book_id, prev_part)
                if text:
                    await update_user_data(chat_id, {"current_part": prev_part})
                    formatted_text = await format_text_with_ai(text, chat_id, bot)
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text=f"Фрагмент {prev_part} из {total_parts}", callback_data="dummy")],
                        [InlineKeyboardButton(text="Озвучить текст", callback_data=f"voice_{book_id}_{prev_part}")]
                    ])
                    try:
                        await bot.send_message(chat_id, formatted_text, reply_markup=keyboard, parse_mode='HTML')
                        logging.info(f"Пользователь {chat_id} перешел к предыдущему фрагменту {prev_part}")
                    except Exception as e:
                        logging.error(f"Ошибка при отправке сообщения: {e}")
                        await bot.send_message(chat_id, text, reply_markup=keyboard)
                else:
                    await message.answer("Это первый фрагмент книги.", reply_markup=get_main_keyboard())
            else:
                await message.answer("Это первый фрагмент книги.", reply_markup=get_main_keyboard())
        else:
            await message.answer("Книга не выбрана. Используйте /selectbook.", reply_markup=get_main_keyboard())

    @dp.message(lambda message: message.text == "Выбор книги")
    async def cmd_selectbook_button(message: types.Message):
        """Обработчик кнопки 'Выбор книги'."""
        from bot import cmd_selectbook
        await cmd_selectbook(message)

    @dp.message(lambda message: message.text == "Расписание")
    async def cmd_schedule_button(message: types.Message, state: FSMContext):
        """Обработчик кнопки 'Расписание'."""
        from bot import cmd_schedule
        await cmd_schedule(message, state)

    @dp.message(lambda message: message.text == "Открыть веб-приложение")
    async def cmd_webapp_button(message: types.Message):
        """Обработчик кнопки 'Открыть веб-приложение'."""
        from bot import cmd_webapp
        await cmd_webapp(message)

    @dp.message(lambda message: message.text == "Управление загрузкой")
    async def cmd_manage_upload(message: types.Message):
        """Обработчик кнопки 'Управление загрузкой'."""
        await message.answer("Выберите действие:", reply_markup=get_manage_upload_keyboard())

    @dp.message(lambda message: message.text == "Загрузить текст")
    async def cmd_upload_text_button(message: types.Message):
        """Обработчик кнопки 'Загрузить текст'."""
        from bot import cmd_upload_text
        await cmd_upload_text(message)

    @dp.message(lambda message: message.text == "Удалить книгу")
    async def cmd_deletebook_button(message: types.Message):
        """Обработчик кнопки 'Удалить книгу'."""
        from bot import cmd_deletebook
        await cmd_deletebook(message)

    @dp.message(lambda message: message.text == "Назад")
    async def cmd_back(message: types.Message):
        """Обработчик кнопки 'Назад' для возврата в главное меню."""
        await message.answer("Вы вернулись в главное меню.", reply_markup=get_main_keyboard())

    @dp.message(lambda message: message.text == "Читать сейчас")
    async def cmd_read_now(message: types.Message):
        """Обработчик кнопки 'Читать сейчас' для немедленного чтения текущего фрагмента."""
        from bot import send_daily_part
        await send_daily_part(message.chat.id, bot)
        logging.info(f"Пользователь {message.chat.id} запросил чтение текущего фрагмента")

    @dp.callback_query(lambda c: c.data.startswith('voice_'))
    async def voice_text_callback(callback_query: types.CallbackQuery):
        """Обработчик кнопки 'Озвучить текст' для генерации и отправки аудио."""
        from database import get_part_text, get_user_data
        _, book_id, part_number = callback_query.data.split('_')
        book_id = int(book_id)
        part_number = int(part_number)
        chat_id = callback_query.from_user.id
        user_data = await get_user_data(chat_id)
        voice = user_data.get('preferred_voice') or "Alloy" if user_data else "Alloy"
        text = await get_part_text(book_id, part_number)
        if text:
            audio_bytes = await generate_audio(text, voice, chat_id=chat_id, bot=bot)
            if audio_bytes:
                audio_file = BufferedInputFile(audio_bytes, filename="audio.mp3")
                await bot.send_audio(chat_id, audio_file)
            else:
                await bot.send_message(chat_id, "Не удалось сгенерировать аудио.")
        else:
            await bot.send_message(chat_id, "Текст не найден.")
        await callback_query.answer()