from aiogram.fsm.state import State, StatesGroup


class ExpenseFlow(StatesGroup):
    month = State()
    category = State()
    day = State()
    amount = State()
    description = State()
    confirm = State()


class IncomeFlow(StatesGroup):
    month = State()
    day = State()
    amount = State()
    description = State()
    confirm = State()
