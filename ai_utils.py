import aiohttp
import asyncio
import logging
from aiogram.exceptions import TelegramBadRequest

TEXT_API_URL = "https://text.pollinations.ai/"
AUDIO_API_URL = "https://text.pollinations.ai/"

async def format_text_with_ai(text, chat_id, bot):
    msg = await bot.send_message(chat_id, "Подождите пожалуйста, готовим лучший формат текста для вас... (10 сек)")
    last_text = "Подождите пожалуйста, готовим лучший формат текста для вас... (10 сек)"
    for i in range(9, -1, -1):
        new_text = f"Подождите пожалуйста, готовим лучший формат текста для вас... ({i} сек)"
        if new_text != last_text:
            try:
                await asyncio.sleep(1)
                await bot.edit_message_text(
                    text=new_text,
                    chat_id=chat_id,
                    message_id=msg.message_id
                )
                last_text = new_text
            except TelegramBadRequest as e:
                if "message is not modified" in str(e):
                    logging.warning(f"Пропущено редактирование сообщения: текст не изменился ({i} сек)")
                    continue
                else:
                    logging.error(f"Ошибка редактирования сообщения: {e}")
                    return text
    payload = {
        "model": "openai",
        "messages": [
            {
                "role": "system",
                "content": "You are an assistant that formats text for better readability in Telegram using HTML. Add logical paragraphs, <b>bold</b>, <i>italic</i>, <code>monospace</code>, <u>underline</u>, and emojis where appropriate. Ensure the text is properly formatted and does not exceed 4096 characters. Return only the formatted text."
            },
            {
                "role": "user",
                "content": f"Please format the following text: {text}"
            }
        ]
    }
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(TEXT_API_URL, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    formatted_text = data['choices'][0]['message']['content']
                    logging.info(f"Длина отформатированного текста: {len(formatted_text)} символов")
                    if len(formatted_text) > 4096:
                        formatted_text = formatted_text[:4096]
                        logging.warning("Текст обрезан до 4096 символов")
                    return formatted_text
                else:
                    logging.error(f"Ошибка форматирования текста: {response.status}")
                    return text
        except Exception as e:
            logging.error(f"Ошибка подключения к API форматирования: {e}")
            return text

async def generate_audio(text, voice="alloy", chat_id=None, bot=None):
    try:
        if chat_id and bot:
            msg = await bot.send_message(chat_id, "Подождите пожалуйста, генерируем аудио... (10 сек)")  # Уменьшено до 10 секунд
            last_text = "Подождите пожалуйста, генерируем аудио... (10 сек)"
            for i in range(29, -1, -1):
                new_text = f"Подождите пожалуйста, генерируем аудио... ({i} сек)"
                if new_text != last_text:
                    try:
                        await asyncio.sleep(1)
                        await bot.edit_message_text(
                            text=new_text,
                            chat_id=chat_id,
                            message_id=msg.message_id
                        )
                        last_text = new_text
                    except TelegramBadRequest as e:
                        if "message is not modified" in str(e):
                            logging.warning(f"Пропущено редактирование сообщения для аудио: текст не изменился ({i} сек)")
                            continue
                        else:
                            logging.error(f"Ошибка редактирования сообщения для аудио: {e}")
                            return None
        payload = {
            "model": "openai-audio",
            "messages": [
                {
                    "role": "system",
                    "content": "You are a text-to-speech system. Read the provided text exactly as it is written, without summarizing, paraphrasing, or modifying it in any way."
                },
                {
                    "role": "user",
                    "content": text
                }
            ],
            "voice": voice.lower()
        }
        logging.info(f"Отправка запроса на {AUDIO_API_URL} с голосом {voice}")
        async with aiohttp.ClientSession() as session:
            async with session.post(AUDIO_API_URL, json=payload) as response:
                if response.status == 200:
                    audio_bytes = await response.read()
                    logging.info(f"Аудио успешно сгенерировано, размер: {len(audio_bytes)} байт")
                    return audio_bytes
                else:
                    logging.error(f"Ошибка API: {response.status}, ответ: {await response.text()}")
                    return None
    except Exception as e:
        logging.error(f"Ошибка генерации аудио: {e}")
        return None