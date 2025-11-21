from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton
)
from config import REACTION_CHOICES, REPORT_REASONS

def build_main_keyboard(is_admin: bool = False) -> ReplyKeyboardMarkup:
    keyboard = [
        [KeyboardButton(text="🔎 Поиск"), KeyboardButton(text="⏭️ Следующий")],
        [KeyboardButton(text="🛑 Стоп"), KeyboardButton(text="⚙️ Настройки")],
    ]
    
    if is_admin:
        keyboard.append([KeyboardButton(text="🛠️ Админ")])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        one_time_keyboard=False,
    )

def build_profile_settings_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Номер телефона")],
            [KeyboardButton(text="📄 Мой профиль"), KeyboardButton(text="🔙 В главное меню")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

def build_admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="👥 Все пользователи")],
            [KeyboardButton(text="🔍 В поиске"), KeyboardButton(text="💬 Диалоги")],
            [KeyboardButton(text="🚫 Заблокированные"), KeyboardButton(text="📝 Жалобы")],
            [KeyboardButton(text="🔙 В главное меню")],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )

def build_reactions_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(text="👍", callback_data="react:like"),
        InlineKeyboardButton(text="👎", callback_data="react:dislike")
    ]
    return InlineKeyboardMarkup(inline_keyboard=[buttons])

def build_phone_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Поделиться номером", request_contact=True)],
            [KeyboardButton(text="❌ Не указывать")],
            [KeyboardButton(text="🔙 Назад в настройки")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )