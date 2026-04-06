"""Teclado de importes rapidos."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

QUICK_AMOUNTS = [5, 10, 15, 20, 30, 50]


def amount_kb() -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for amt in QUICK_AMOUNTS:
        row.append(InlineKeyboardButton(text=str(amt), callback_data=f"amt:{amt}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
