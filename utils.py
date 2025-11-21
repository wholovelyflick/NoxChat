from aiogram import Bot
import asyncio

async def delete_message_with_delay(bot: Bot, chat_id: int, message_id: int, delay: int = 30):  # Увеличиваем до 30 секунд
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass

async def send_temporary_message(bot: Bot, chat_id: int, text: str, reply_markup=None, delay: int = 30):  # Увеличиваем до 30 секунд
    message = await bot.send_message(chat_id, text, reply_markup=reply_markup, parse_mode="HTML")
    asyncio.create_task(delete_message_with_delay(bot, chat_id, message.message_id, delay))
    return message.message_id