from aiogram.fsm.state import State, StatesGroup


class ExpenseFlow(StatesGroup):
    category = State()
    date = State()
    amount = State()
    description = State()
    confirm = State()


class IncomeFlow(StatesGroup):
    date = State()
    amount = State()
    description = State()
    confirm = State()
