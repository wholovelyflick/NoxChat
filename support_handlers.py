from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from database import Database
from keyboards import build_main_keyboard
from config import ADMIN_IDS
from states import SupportStates
from datetime import datetime
import asyncio

router = Router()
db = Database()

support_tickets = {}

def build_support_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📞 Написать в поддержку", callback_data="support_contact")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="support_close")]
        ]
    )

def build_admin_support_keyboard(ticket_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Ответить", callback_data=f"support_reply:{ticket_id}")],
            [InlineKeyboardButton(text="✅ Закрыть тикет", callback_data=f"support_close_ticket:{ticket_id}")]
        ]
    )

@router.message(F.text == "📞 Поддержка")
async def handle_support(message: Message, state: FSMContext):
    user = message.from_user
    if user is None:
        return
    
    await message.answer(
        "📞 Служба поддержки\n\nЗдесь вы можете задать вопрос администрации или сообщить о проблеме.\n\nНапишите ваше сообщение, и мы ответим в ближайшее время:",
        reply_markup=build_support_keyboard()
    )
    await state.set_state(SupportStates.waiting_message)

@router.callback_query(F.data == "support_contact")
async def support_contact_callback(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "📝 Напишите ваше сообщение для поддержки:\n\nОпишите вашу проблему или вопрос максимально подробно.",
    )
    await state.set_state(SupportStates.waiting_message)

@router.message(SupportStates.waiting_message)
async def handle_support_message(message: Message, state: FSMContext, bot: Bot):
    user = message.from_user
    user_info = await db.get_user(user.id)
    
    ticket_id = f"ticket_{user.id}_{int(datetime.now().timestamp())}"
    support_tickets[ticket_id] = {
        'user_id': user.id,
        'username': user_info['username'] if user_info else user.username,
        'message': message.text,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'status': 'open',
        'replies': []
    }
    
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                f"🆕 НОВОЕ ОБРАЩЕНИЕ В ПОДДЕРЖКУ\n\n🎫 ID тикета: {ticket_id}\n👤 Пользователь: {user_info['username'] or 'Аноним'} (ID: {user.id})\n📅 Время: {support_tickets[ticket_id]['timestamp']}\n📝 Сообщение: {message.text}\n\n💬 Для ответа используйте админ-панель → Поддержка",
                reply_markup=build_admin_support_keyboard(ticket_id)
            )
        except Exception:
            pass
    
    await message.answer(
        "✅ Ваше сообщение отправлено в поддержку!\n\nМы ответим вам в ближайшее время. Спасибо за обращение!",
        reply_markup=build_main_keyboard()
    )
    await state.clear()

@router.message(F.text == "🛠️ Админ")
async def handle_admin_main(message: Message, state: FSMContext):
    user = message.from_user
    if user is None or user.id not in ADMIN_IDS:
        await message.answer("❌ Недостаточно прав")
        return
    
    from admin_handlers import build_admin_keyboard
    await message.answer(
        "🛠️ Админ-панель\n\nВыберите раздел:",
        reply_markup=build_admin_keyboard(),
    )