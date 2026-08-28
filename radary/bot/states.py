from aiogram.fsm.state import State, StatesGroup


class AddChat(StatesGroup):
    waiting_input = State()


class AddKeywords(StatesGroup):
    waiting_input = State()


class AddStopWords(StatesGroup):
    waiting_input = State()


class ImportConfig(StatesGroup):
    waiting_file = State()
