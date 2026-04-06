from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💸 Gasto", callback_data="menu:expense"),
            InlineKeyboardButton(text="💰 Ingreso", callback_data="menu:income"),
        ],
        [
            InlineKeyboardButton(text="📊 Consultar", callback_data="menu:query"),
            InlineKeyboardButton(text="📋 Ultimos", callback_data="menu:recent"),
        ],
    ])
