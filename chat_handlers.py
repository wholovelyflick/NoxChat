from aiogram import Router, F, Bot
from aiogram.filters import Command
from aiogram.types import Message
from database import Database
from keyboards import build_main_keyboard, build_reactions_keyboard
from config import ADMIN_IDS, DEVELOPER_ID

router = Router()
db = Database()

async def is_admin(user_id: int) -> bool:
    if user_id == DEVELOPER_ID or user_id in ADMIN_IDS:
        return True
    user_info = await db.get_user(user_id)
    return user_info and user_info.get('is_admin')

async def end_dialog_and_notify(bot: Bot, you_id: int) -> int:
    partner = await db.end_dialog_for(you_id)
    if partner is not None:
        try:
            is_admin_user = await is_admin(partner)
            await bot.send_message(partner, "💔 Собеседник завершил диалог", reply_markup=build_main_keyboard(is_admin_user))
            
            # Отправляем кнопки оценки после завершения диалога
            await bot.send_message(
                partner,
                "💭 Если хотите, оставьте мнение о вашем собеседнике. Это поможет находить вам подходящих собеседников:",
                reply_markup=build_reactions_keyboard()
            )
        except Exception:
            pass
    return partner

@router.message(F.text == "🔎 Поиск")
@router.message(Command("search"))
async def handle_search(message: Message, bot: Bot):
    user = message.from_user
    if user is None:
        return
    
    await db.ensure_user(user.id, user.username)
    
    if await db.is_blocked(user.id):
        is_admin_user = await is_admin(user.id)
        await message.answer("🚫 Ваш аккаунт заблокирован администратором", reply_markup=build_main_keyboard(is_admin_user))
        return
    
    profile = await db.get_profile(user.id)
    if not profile.get('phone_number'):
        is_admin_user = await is_admin(user.id)
        await message.answer("❌ Сначала укажите номер телефона в настройках!", reply_markup=build_main_keyboard(is_admin_user))
        return
    
    await db.set_in_search(user.id, True)
    partner_id = await db.find_match(user.id)
    
    if partner_id is None:
        is_admin_user = await is_admin(user.id)
        await message.answer("🔍 Ищу собеседника... Ожидайте ⏳", reply_markup=build_main_keyboard(is_admin_user))
        return
    
    is_admin_user = await is_admin(user.id)
    await message.answer("✅ Собеседник найден!\n\n💬 Можете начинать общение!", reply_markup=build_main_keyboard(is_admin_user))
    
    try:
        partner_admin_status = await is_admin(partner_id)
        await bot.send_message(partner_id, "✅ Собеседник найден!\n\n💬 Можете начинать общение!", reply_markup=build_main_keyboard(partner_admin_status))
    except Exception:
        pass

@router.message(F.text == "🛑 Стоп")
@router.message(Command("stop"))
async def handle_stop(message: Message, bot: Bot):
    user = message.from_user
    if user is None:
        return
    
    partner_id = await end_dialog_and_notify(bot, user.id)
    await db.set_in_search(user.id, False)
    
    is_admin_user = await is_admin(user.id)
    if partner_id:
        await message.answer("💔 Диалог завершён\n\nНажмите «🔎 Поиск» чтобы найти нового собеседника", reply_markup=build_main_keyboard(is_admin_user))
        
        # Отправляем кнопки оценки после завершения диалога
        await message.answer(
            "💭 Если хотите, оставьте мнение о вашем собеседнике. Это поможет находить вам подходящих собеседников:",
            reply_markup=build_reactions_keyboard()
        )
    else:
        await message.answer("ℹ️ У вас нет активного диалога", reply_markup=build_main_keyboard(is_admin_user))

@router.message(F.text == "⏭️ Следующий")
@router.message(Command("next"))
async def handle_next(message: Message, bot: Bot):
    user = message.from_user
    if user is None:
        return
    
    partner_id = await end_dialog_and_notify(bot, user.id)
    
    # Отправляем кнопки оценки перед поиском нового
    if partner_id:
        await message.answer(
            "💭 Если хотите, оставьте мнение о вашем собеседнике. Это поможет находить вам подходящих собеседников:",
            reply_markup=build_reactions_keyboard()
        )
    
    await db.set_in_search(user.id, True)
    new_partner_id = await db.find_match(user.id)
    
    is_admin_user = await is_admin(user.id)
    if new_partner_id is None:
        await message.answer("🔍 Ищу нового собеседника... ⏳", reply_markup=build_main_keyboard(is_admin_user))
        return
    
    await message.answer("🔄 Новый собеседник найден!\n\n💬 Можете начинать общение!", reply_markup=build_main_keyboard(is_admin_user))
    
    try:
        partner_admin_status = await is_admin(new_partner_id)
        await bot.send_message(new_partner_id, "🔄 Новый собеседник найден!\n\n💬 Можете начинать общение!", reply_markup=build_main_keyboard(partner_admin_status))
    except Exception:
        pass

def is_not_command(text: str) -> bool:
    commands = [
        "🛠️ Админ", "🔎 Поиск", "⏭️ Следующий", 
        "🛑 Стоп", "⚙️ Настройки",
        "📊 Статистика", "👥 Все пользователи", "🔍 В поиске", 
        "💬 Диалоги", "🚫 Заблокированные", "📝 Жалобы",
        "🔙 В главное меню",
        "📱 Номер телефона", "📄 Мой профиль", "🔙 Назад в настройки"
    ]
    return text not in commands

@router.message(
    F.text & 
    ~F.text.startswith("/") & 
    F.func(lambda message: is_not_command(message.text))
)
@router.message(F.photo & ~F.caption.startswith("/"))
@router.message(F.document & ~F.caption.startswith("/"))
@router.message(F.sticker)
@router.message(F.voice & ~F.caption.startswith("/"))
@router.message(F.video & ~F.caption.startswith("/"))
@router.message(F.video_note)
@router.message(F.animation & ~F.caption.startswith("/"))
@router.message(F.audio & ~F.caption.startswith("/"))
async def relay_message(message: Message, bot: Bot):
    user = message.from_user
    if user is None:
        return
    
    if await db.is_blocked(user.id):
        is_admin_user = await is_admin(user.id)
        await message.answer("🚫 Ваш аккаунт заблокирован", reply_markup=build_main_keyboard(is_admin_user))
        return
    
    partner = await db.get_partner(user.id)
    if partner is None:
        is_admin_user = await is_admin(user.id)
        await message.answer("❌ У вас нет активного собеседника", reply_markup=build_main_keyboard(is_admin_user))
        return
    
    try:
        if message.text:
            partner_admin_status = await is_admin(partner)
            await bot.send_message(partner, message.text, reply_markup=build_main_keyboard(partner_admin_status))
        elif message.photo:
            photo = message.photo[-1]
            caption = message.caption or ""
            partner_admin_status = await is_admin(partner)
            await bot.send_photo(partner, photo.file_id, caption=caption, reply_markup=build_main_keyboard(partner_admin_status))
        elif message.document:
            caption = message.caption or ""
            partner_admin_status = await is_admin(partner)
            await bot.send_document(partner, message.document.file_id, caption=caption, reply_markup=build_main_keyboard(partner_admin_status))
        elif message.sticker:
            partner_admin_status = await is_admin(partner)
            await bot.send_sticker(partner, message.sticker.file_id, reply_markup=build_main_keyboard(partner_admin_status))
        elif message.voice:
            caption = message.caption or ""
            partner_admin_status = await is_admin(partner)
            await bot.send_voice(partner, message.voice.file_id, caption=caption, reply_markup=build_main_keyboard(partner_admin_status))
        elif message.video:
            caption = message.caption or ""
            partner_admin_status = await is_admin(partner)
            await bot.send_video(partner, message.video.file_id, caption=caption, reply_markup=build_main_keyboard(partner_admin_status))
        elif message.video_note:
            partner_admin_status = await is_admin(partner)
            await bot.send_video_note(partner, message.video_note.file_id, reply_markup=build_main_keyboard(partner_admin_status))
        elif message.animation:
            caption = message.caption or ""
            partner_admin_status = await is_admin(partner)
            await bot.send_animation(partner, message.animation.file_id, caption=caption, reply_markup=build_main_keyboard(partner_admin_status))
        elif message.audio:
            caption = message.caption or ""
            partner_admin_status = await is_admin(partner)
            await bot.send_audio(partner, message.audio.file_id, caption=caption, reply_markup=build_main_keyboard(partner_admin_status))
    except Exception as e:
        is_admin_user = await is_admin(user.id)
        await message.answer("❌ Не удалось отправить сообщение. Возможно, собеседник отключился.", reply_markup=build_main_keyboard(is_admin_user))