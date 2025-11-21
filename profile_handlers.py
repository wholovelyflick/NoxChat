from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, Contact

from database import Database
from keyboards import (
    build_main_keyboard, build_profile_settings_keyboard
)
from states import ProfileStates
from config import ADMIN_IDS, DEVELOPER_ID

router = Router()
db = Database()

async def is_admin(user_id: int) -> bool:
    if user_id == DEVELOPER_ID or user_id in ADMIN_IDS:
        return True
    user_info = await db.get_user(user_id)
    return user_info and user_info.get('is_admin')

@router.message(Command("start"))
async def handle_start(message: Message, bot: Bot, state: FSMContext):
    user = message.from_user
    if user is None:
        return
    
    await db.ensure_user(tg_id=user.id, username=user.username)
    
    is_admin_user = await is_admin(user.id)
    kb = build_main_keyboard(is_admin_user)
    
    await message.answer(
        "👋 Привет! Добро пожаловать в школьный чат!\n\n🔍 Нажми «Поиск» чтобы найти собеседника\n⚙️ «Настройки» чтобы посмотреть профиль",
        reply_markup=kb
    )

@router.message(F.text == "⚙️ Настройки")
async def handle_settings(message: Message, state: FSMContext, bot: Bot):
    await message.answer(
        "⚙️ Настройки профиля\n\nВыберите что хотите настроить:",
        reply_markup=build_profile_settings_keyboard()
    )
    await state.set_state(ProfileStates.settings)

@router.message(ProfileStates.settings, F.text == "📄 Мой профиль")
async def settings_show_profile(message: Message, state: FSMContext, bot: Bot):
    await handle_profile_view(message, bot)

@router.message(ProfileStates.settings, F.text == "🔙 В главное меню")
async def settings_back_to_main(message: Message, state: FSMContext, bot: Bot):
    is_admin_user = await is_admin(message.from_user.id)
    await message.answer("🔙 Возвращаемся в главное меню", reply_markup=build_main_keyboard(is_admin_user))
    await state.clear()

@router.message(F.text == "📄 Профиль")
async def handle_profile_view(message: Message, bot: Bot):
    info = await db.get_user(message.from_user.id)
    if not info:
        await message.answer("❌ Профиль не найден")
        return
    
    username = f"@{info['username']}" if info['username'] else "❌ Не указан"
    
    text = (
        "📊 Ваш профиль\n\n"
        f"🆔 ID: {info['tg_id']}\n"
        f"👤 Username: {username}\n"
        f"📅 Регистрация: {info['registered_at'][:16]}\n"
        f"👑 Статус: {'⭐ Администратор' if info['is_admin'] else '👤 Пользователь'}\n\n"
        "⚙️ Чтобы изменить настройки, нажмите «Настройки»"
    )
    is_admin_user = await is_admin(message.from_user.id)
    await message.answer(text, reply_markup=build_main_keyboard(is_admin_user))