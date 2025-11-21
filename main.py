import asyncio
import os
from aiogram import Bot, Dispatcher

from config import BOT_TOKEN, GITHUB_TOKEN, GITHUB_REPO_OWNER, GITHUB_REPO_NAME, GITHUB_DB_FILE
from database import Database
from profile_handlers import router as profile_router
from chat_handlers import router as chat_router
from admin_handlers import router as admin_router
from reaction_handlers import router as reaction_router

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не задан")
    
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    # Инициализация GitHub базы данных
    db = Database(
        github_token=GITHUB_TOKEN,
        repo_owner=GITHUB_REPO_OWNER,
        repo_name=GITHUB_REPO_NAME,
        db_file=GITHUB_DB_FILE
    )
    await db.init()
    
    dp.include_router(profile_router)
    dp.include_router(chat_router)
    dp.include_router(admin_router)
    dp.include_router(reaction_router)

    print("🎓 Школьный чат запущен! Нажмите Ctrl+C для остановки")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ Критическая ошибка: {e}")
    finally:
        await db.close()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())