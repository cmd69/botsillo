from aiogram.fsm.state import State, StatesGroup


class ExpenseFlow(StatesGroup):
    date = State()
    category = State()
    amount = State()
    description = State()
    confirm = State()


class IncomeFlow(StatesGroup):
    date = State()
    amount = State()
    description = State()
    confirm = State()
