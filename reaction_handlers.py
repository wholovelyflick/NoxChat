from aiogram import Router, F, Bot

from aiogram.fsm.context import FSMContext

from aiogram.types import Message, CallbackQuery



from database import Database

from keyboards import build_main_keyboard

from config import ADMIN_IDS, DEVELOPER_ID



router = Router()

db = Database()



async def is_admin(user_id: int) -> bool:

    if user_id == DEVELOPER_ID or user_id in ADMIN_IDS:

        return True

    user_info = await db.get_user(user_id)

    return user_info and user_info.get('is_admin')



@router.callback_query(F.data.startswith("react:"))

async def handle_reaction(call: CallbackQuery, state: FSMContext, bot: Bot) -> None:

    user_id = call.from_user.id

    reaction_type = call.data.split(":")[1]

    

    if reaction_type == "like":

        reaction_text = "👍 Лайк"

    else:

        reaction_text = "👎 Дизлайк"

    

    await call.message.edit_text(f"✅ Спасибо за оценку: {reaction_text}")

    

    # Уведомляем админов о реакции

    for admin_id in ADMIN_IDS:

        try:

            user_info = await db.get_user(user_id)

            await bot.send_message(

                admin_id,

                f"🎭 Новая реакция\n\n👤 Пользователь: {user_info['username'] or 'Аноним'} (ID: {user_id})\n📊 Реакция: {reaction_text}",

            )

        except Exception:

            pass

    

    # Возвращаем главное меню

    is_admin_user = await is_admin(user_id)

    await call.message.answer("Выберите действие:", reply_markup=build_main_keyboard(is_admin_user))