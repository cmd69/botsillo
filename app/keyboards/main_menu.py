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
        [InlineKeyboardButton(text="🔍 Consultar", callback_data="pf:consult")],
        [InlineKeyboardButton(text="💸 Nuevo gasto", callback_data="pf:expense")],
        [InlineKeyboardButton(text="💰 Nuevo ingreso", callback_data="pf:income")],
        [InlineKeyboardButton(text="↩️ Volver", callback_data="main_menu")],
    ])
