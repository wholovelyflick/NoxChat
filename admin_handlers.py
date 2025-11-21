from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
import asyncio
from datetime import datetime

from database import Database
from keyboards import build_main_keyboard, build_admin_keyboard
from states import AdminStates
from config import ADMIN_IDS, DEVELOPER_ID
from storage import storage

router = Router()
db = Database()

support_tickets = {}
broadcast_messages = {}

async def is_admin(user_id: int) -> bool:
    if user_id == DEVELOPER_ID:
        return True
    user_info = await db.get_user(user_id)
    if user_info and user_info.get('is_admin'):
        return True
    return user_id in ADMIN_IDS

def build_user_management_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"admin_block:{user_id}"),
                InlineKeyboardButton(text="✅ Разблокировать", callback_data=f"admin_unblock:{user_id}")
            ],
            [
                InlineKeyboardButton(text="💞 Соединить с...", callback_data=f"admin_pair_start:{user_id}"),
                InlineKeyboardButton(text="🔍 Подробно", callback_data=f"admin_info:{user_id}")
            ],
            [
                InlineKeyboardButton(text="👑 Сделать админом", callback_data=f"admin_make_admin:{user_id}")
            ]
        ]
    )

@router.message(F.text == "🛠️ Админ")
async def handle_admin_main(message: Message, state: FSMContext, bot: Bot):
    user = message.from_user
    if user is None or not await is_admin(user.id):
        await message.answer("❌ Недостаточно прав")
        return
    
    await message.answer(
        "🎛️ Админ-панель\n\nВыберите раздел:",
        reply_markup=build_admin_keyboard()
    )
    await state.set_state(AdminStates.main)

@router.message(AdminStates.main, F.text == "👤 Управление пользователями")
async def admin_user_management(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    
    await message.answer(
        "👤 Управление пользователями\n\nВведите ID пользователя для управления:"
    )
    await state.set_state(AdminStates.user_management)

@router.message(AdminStates.user_management)
async def admin_user_manage(message: Message, state: FSMContext, bot: Bot):
    if not message.text.isdigit():
        await message.answer("❌ Введите корректный ID пользователя (только цифры)")
        return
    
    user_id = int(message.text)
    user_info = await db.get_user(user_id)
    
    if not user_info:
        await message.answer("❌ Пользователь не найден")
        return
    
    status = "🚫 Заблокирован" if user_info['blocked'] else "✅ Активен"
    
    await message.answer(
        f"👤 Информация о пользователе\n\n🆔 ID: {user_id}\n👤 Username: @{user_info['username'] or 'нет'}\n📅 Регистрация: {user_info['registered_at'][:16]}\n🔍 В поиске: {'✅ Да' if user_info['in_search'] else '❌ Нет'}\n💬 В диалоге: {'✅ Да' if user_info['partner_tg_id'] else '❌ Нет'}\n🔒 Статус: {status}\n👑 Админ: {'✅ Да' if user_info['is_admin'] else '❌ Нет'}",
        reply_markup=build_user_management_keyboard(user_id)
    )

@router.callback_query(F.data.startswith("admin_block:"))
async def admin_block_user(call: CallbackQuery, bot: Bot):
    if not await is_admin(call.from_user.id):
        await call.answer("❌ Недостаточно прав")
        return
        
    user_id = int(call.data.split(":")[1])
    
    await db.set_blocked(user_id, True)
    
    try:
        await bot.send_message(
            user_id,
            "🚫 Ваш аккаунт заблокирован администратором\n\nВы больше не можете использовать бота.",
        )
    except Exception:
        pass
    
    await call.answer("✅ Пользователь заблокирован")
    user_info = await db.get_user(user_id)
    
    await call.message.edit_text(
        f"👤 Информация о пользователе\n\n🆔 ID: {user_id}\n👤 Username: @{user_info['username'] or 'нет'}\n📅 Регистрация: {user_info['registered_at'][:16]}\n🔒 Статус: 🚫 Заблокирован\n👑 Админ: {'✅ Да' if user_info['is_admin'] else '❌ Нет'}\n\n🔒 Пользователь заблокирован",
        reply_markup=build_user_management_keyboard(user_id)
    )

@router.callback_query(F.data.startswith("admin_unblock:"))
async def admin_unblock_user(call: CallbackQuery, bot: Bot):
    if not await is_admin(call.from_user.id):
        await call.answer("❌ Недостаточно прав")
        return
        
    user_id = int(call.data.split(":")[1])
    
    await db.set_blocked(user_id, False)
    
    try:
        await bot.send_message(
            user_id,
            "✅ Ваш аккаунт разблокирован администратором\n\nТеперь вы снова можете пользоваться чатом!",
        )
    except Exception:
        pass
    
    await call.answer("✅ Пользователь разблокирован")
    user_info = await db.get_user(user_id)
    
    await call.message.edit_text(
        f"👤 Информация о пользователе\n\n🆔 ID: {user_id}\n👤 Username: @{user_info['username'] or 'нет'}\n📅 Регистрация: {user_info['registered_at'][:16]}\n🔒 Статус: ✅ Активен\n👑 Админ: {'✅ Да' if user_info['is_admin'] else '❌ Нет'}\n\n🔓 Пользователь разблокирован",
        reply_markup=build_user_management_keyboard(user_id)
    )

@router.callback_query(F.data.startswith("admin_pair_start:"))
async def admin_pair_start(call: CallbackQuery, state: FSMContext, bot: Bot):
    if not await is_admin(call.from_user.id):
        await call.answer("❌ Недостаточно прав")
        return
        
    user1_id = int(call.data.split(":")[1])
    await state.update_data(pair_user1=user1_id)
    await call.message.answer(
        f"💞 Соединение пользователей\n\nПользователь 1: ID {user1_id}\nВведите ID второго пользователя для соединения:"
    )
    await state.set_state(AdminStates.user_management)

@router.callback_query(F.data.startswith("admin_make_admin:"))
async def admin_make_admin(call: CallbackQuery, bot: Bot):
    if not await is_admin(call.from_user.id):
        await call.answer("❌ Недостаточно прав")
        return
        
    user_id = int(call.data.split(":")[1])
    
    await db.set_admin(user_id, True)
    await call.answer("✅ Пользователь назначен администратором")
    
    user_info = await db.get_user(user_id)
    
    await call.message.edit_text(
        f"👤 Информация о пользователе\n\n🆔 ID: {user_id}\n👤 Username: @{user_info['username'] or 'нет'}\n📅 Регистрация: {user_info['registered_at'][:16]}\n🔒 Статус: {'🚫 Заблокирован' if user_info['blocked'] else '✅ Активен'}\n👑 Админ: ✅ Да\n\n👑 Пользователь назначен администратором",
        reply_markup=build_user_management_keyboard(user_id)
    )

@router.message(AdminStates.main, F.text == "📊 Статистика")
async def admin_stats(message: Message, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    
    total_users, searching_users, active_dialogs = await db.stats()
    
    blocked_users = await db.get_blocked_users()
    new_today = await db.get_recent_users(1)
    admins_list = await db.get_admins()
    
    stats_text = (
        "📊 Статистика школьного чата\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"🔍 В поиске: {searching_users}\n"
        f"💬 Активных диалогов: {active_dialogs}\n"
        f"🚫 Заблокированных: {len(blocked_users)}\n"
        f"🆕 Новых за сутки: {new_today}\n"
        f"👑 Администраторов: {len(admins_list)}"
    )
    await message.answer(stats_text)

@router.message(AdminStates.main, F.text == "👥 Все пользователи")
async def admin_all_users(message: Message, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    
    all_users = await db.get_all_users(5000)
    
    if not all_users:
        await message.answer("❌ Пользователей не найдено")
        return
    
    user_list = "👥 Все пользователи:\n\n"
    for i, (tg_id, username, reg_date, blocked, is_admin_user) in enumerate(all_users, 1):
        status = "🚫" if blocked else "✅"
        admin_emoji = "👑" if is_admin_user else ""
        
        user_list += f"{i}. {status} {admin_emoji} ID: {tg_id}\n"
        user_list += f"   👤 @{username or 'нет'}\n"
        user_list += f"   📅 {reg_date[:10]}\n\n"
    
    await message.answer(user_list)

@router.message(AdminStates.main, F.text == "🔍 В поиске")
async def admin_searching(message: Message, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    
    searching = await db.list_searching(5000)
    
    if not searching:
        await message.answer("❌ Никто не ищет собеседника")
        return
    
    search_text = "🔍 Пользователи в поиске:\n\n"
    for i, user_id in enumerate(searching, 1):
        user_info = await db.get_user(user_id)
        if user_info:
            search_text += f"{i}. ID: {user_id}\n"
            search_text += f"   👤 @{user_info['username'] or 'нет'}\n\n"
    
    await message.answer(search_text)

@router.message(AdminStates.main, F.text == "💬 Диалоги")
async def admin_dialogs(message: Message, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    
    pairs = await db.list_dialog_pairs(20)
    
    if not pairs:
        await message.answer("❌ Активных диалогов нет")
        return
    
    dialogs_text = "💬 Активные диалоги:\n\n"
    for i, (user1, user2) in enumerate(pairs, 1):
        user1_info = await db.get_user(user1)
        user2_info = await db.get_user(user2)
        
        dialogs_text += f"{i}. 💞 Диалог #{i}\n"
        dialogs_text += f"   👤 {user1_info['username'] or 'Аноним'} (ID: {user1})\n"
        dialogs_text += f"   👤 {user2_info['username'] or 'Аноним'} (ID: {user2})\n\n"
    
    await message.answer(dialogs_text)

@router.message(AdminStates.main, F.text == "🚫 Заблокированные")
async def admin_blocked(message: Message, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    
    blocked_users = await db.get_blocked_users()
    
    if not blocked_users:
        await message.answer("✅ Нет заблокированных пользователей")
        return
    
    blocked_text = "🚫 Заблокированные пользователи:\n\n"
    for i, (tg_id, username, reg_date) in enumerate(blocked_users, 1):
        blocked_text += f"{i}. ID: {tg_id}\n"
        blocked_text += f"   👤 @{username or 'нет'}\n"
        blocked_text += f"   📅 {reg_date[:10]}\n\n"
    
    await message.answer(blocked_text)

@router.message(AdminStates.main, F.text == "📝 Жалобы")
async def admin_reports(message: Message, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    
    reports = storage.get_reports()
    
    if not reports:
        await message.answer("✅ Жалоб нет")
        return
    
    reports_text = "📝 Последние жалобы:\n\n"
    report_count = 0
    
    for reporter_id, user_reports in list(reports.items())[-10:]:
        reporter_info = await db.get_user(reporter_id)
        if reporter_info:
            reports_text += f"👤 {reporter_info['username'] or 'Аноним'} (ID: {reporter_id})\n"
            
            for report in user_reports[-3:]:
                report_count += 1
                reason_map = {
                    "insults": "🚫 Оскорбления",
                    "inappropriate": "🔞 Неподобающий контент", 
                    "spam": "💼 Реклама/спам",
                    "bad_behavior": "🎭 Неадекватное поведение",
                    "other": "📵 Другое"
                }
                reports_text += f"   📋 {reason_map.get(report['reason'], report['reason'])}\n"
                if report.get('details'):
                    details = report['details'][:100] + "..." if len(report['details']) > 100 else report['details']
                    reports_text += f"   📄 {details}\n"
                reports_text += f"   ⏰ {report['timestamp']}\n\n"
    
    if report_count == 0:
        await message.answer("✅ Активных жалоб нет")
    else:
        await message.answer(reports_text)

@router.message(AdminStates.main, F.text == "👑 Управление админами")
async def admin_management(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    
    await message.answer(
        "👑 Управление администраторами\n\nДля добавления/удаления админов используйте команды:\n\n"
        "Добавить админа: /add_admin [user_id]\n"
        "Удалить админа: /remove_admin [user_id]\n"
        "Список админов: /list_admins"
    )

@router.message(AdminStates.main, F.text == "🔙 В главное меню")
async def admin_back_to_main_menu(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
    
    user_info = await db.get_user(message.from_user.id)
    is_admin_user = user_info and (user_info.get('is_admin') or message.from_user.id in ADMIN_IDS)
    await message.answer("🔙 Возвращаемся в главное меню", reply_markup=build_main_keyboard(is_admin_user))
    await state.clear()

# Добавляем обработчик для соединения пользователей
@router.message(AdminStates.user_management)
async def admin_pair_users(message: Message, state: FSMContext, bot: Bot):
    if not await is_admin(message.from_user.id):
        return
        
    if not message.text.isdigit():
        await message.answer("❌ Введите корректный ID пользователя (только цифры)")
        return
    
    user2_id = int(message.text)
    state_data = await state.get_data()
    user1_id = state_data.get('pair_user1')
    
    if not user1_id:
        await message.answer("❌ Ошибка: не найден первый пользователь")
        await state.set_state(AdminStates.main)
        return
    
    # Соединяем пользователей
    await db.force_pair(user1_id, user2_id)
    
    # Уведомляем пользователей
    try:
        user1_info = await db.get_user(user1_id)
        is_admin_user1 = await is_admin(user1_id)
        await bot.send_message(user1_id, "🔗 Администратор соединил вас с собеседником!", reply_markup=build_main_keyboard(is_admin_user1))
    except Exception:
        pass
    
    try:
        user2_info = await db.get_user(user2_id)
        is_admin_user2 = await is_admin(user2_id)
        await bot.send_message(user2_id, "🔗 Администратор соединил вас с собеседником!", reply_markup=build_main_keyboard(is_admin_user2))
    except Exception:
        pass
    
    await message.answer(f"✅ Пользователи {user1_id} и {user2_id} соединены!")
    await state.set_state(AdminStates.main)