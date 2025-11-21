from aiogram.fsm.state import StatesGroup, State

class ProfileStates(StatesGroup):
    settings = State()

class AdminStates(StatesGroup):
    main = State()
    user_management = State()

class ReportStates(StatesGroup):
    waiting_reason = State()
    waiting_details = State()

class SupportStates(StatesGroup):
    waiting_message = State()