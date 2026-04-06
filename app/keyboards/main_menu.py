from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Nuevo Gasto", callback_data="menu:expense"),
            InlineKeyboardButton(text="Nuevo Ingreso", callback_data="menu:income"),
        ],
        [
            InlineKeyboardButton(text="Resumen Mes", callback_data="menu:summary"),
            InlineKeyboardButton(text="Ultimos 10", callback_data="menu:recent"),
        ],
    ])
