from aiogram.fsm.state import State, StatesGroup

class SearchUser(StatesGroup):
    waiting_query = State()

class EditWelcome(StatesGroup):
    waiting_text = State()

class Broadcast(StatesGroup):
    select_role = State()
    waiting_message = State()
    confirm = State()