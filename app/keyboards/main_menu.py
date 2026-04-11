from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    """Menu raiz: Gastos (submenu) y Portfolio."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💸 Gastos", callback_data="menu:root_expenses"),
            InlineKeyboardButton(text="📈 Portfolio", callback_data="menu:root_portfolio"),
        ],
    ])


def expenses_menu_kb() -> InlineKeyboardMarkup:
    """Submenu de gastos/ingresos/consultas (antes era el menu principal)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💸 Gasto", callback_data="menu:expense"),
            InlineKeyboardButton(text="💰 Ingreso", callback_data="menu:income"),
        ],
        [
            InlineKeyboardButton(text="📊 Consultar", callback_data="menu:query"),
            InlineKeyboardButton(text="📋 Ultimos", callback_data="menu:recent"),
        ],
        [InlineKeyboardButton(text="↩️ Volver", callback_data="main_menu")],
    ])


def portfolio_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Consultar", callback_data="pf:consult"),
            InlineKeyboardButton(text="Transaccion", callback_data="pf:tx_menu"),
        ],
        [
            InlineKeyboardButton(text="Movimiento", callback_data="pf:movement"),
            InlineKeyboardButton(text="Atras", callback_data="main_menu"),
        ],
    ])


def portfolio_tx_submenu_kb() -> InlineKeyboardMarkup:
    """Compra/Venta de activos (tras pulsar Transacción)."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Compra", callback_data="pf:expense"),
            InlineKeyboardButton(text="Venta", callback_data="pf:income"),
        ],
        [InlineKeyboardButton(text="Atras", callback_data="pf:menu")],
    ])
