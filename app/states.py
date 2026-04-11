from aiogram.fsm.state import State, StatesGroup


class ExpenseFlow(StatesGroup):
    category = State()
    subcategory = State()
    month = State()
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


class QueryFlow(StatesGroup):
    month = State()
    detail = State()


class PortfolioFlow(StatesGroup):
    """Consulta u operacion (buy/sell) en billetera de inversion."""

    picking_wallet = State()
    consult_after_ficha = State()
    op_after_ficha = State()
    op_asset = State()
    op_quantity = State()
    op_price = State()
    op_total = State()
    op_fees = State()
    op_month = State()
    op_day = State()
    op_notes = State()
    op_confirm = State()
