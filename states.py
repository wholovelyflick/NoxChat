from aiogram.fsm.state import StatesGroup, State



class ProfileStates(StatesGroup):

    settings = State()

    phone_number = State()



class AdminStates(StatesGroup):

    main = State()

    quick_actions = State()

    broadcast = State()

    user_management = State()

    admin_management = State()

    add_admin = State()

    remove_admin = State()

    support_reply = State()



class ReportStates(StatesGroup):

    waiting_reason = State()

    waiting_details = State()



class SupportStates(StatesGroup):

    waiting_message = State()