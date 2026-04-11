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
    wallet_hub = State()
    op_asset = State()
    op_quantity = State()
    op_price = State()
    op_total = State()
    op_fees = State()
    op_month = State()
    op_day = State()
    op_notes = State()
    op_confirm = State()
    # Movimiento de capital (EUR -> billetera)
    mov_bank = State()
    mov_pick_dir = State()
    mov_amount = State()
    mov_month = State()
    mov_day = State()
    mov_desc = State()
    mov_confirm = State()
