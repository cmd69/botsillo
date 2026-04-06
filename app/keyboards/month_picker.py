"""Month picker simple para resumen (no usa DetailedTelegramCalendar)."""
from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

MONTHS_ES = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]


def month_picker_kb(year: int | None = None, prefix: str = "month") -> InlineKeyboardMarkup:
    """Teclado 4x3 con los meses del anyo. callback_data = '<prefix>:YYYY-MM'."""
    if year is None:
        year = date.today().year

    year_prefix = f"{prefix}_year"

    rows: list[list[InlineKeyboardButton]] = []
    for row_start in range(0, 12, 4):
        row = []
        for i in range(row_start, row_start + 4):
            month_num = i + 1
            label = MONTHS_ES[i]
            cb = f"{prefix}:{year}-{month_num:02d}"
            row.append(InlineKeyboardButton(text=label, callback_data=cb))
        rows.append(row)

    rows.append([
        InlineKeyboardButton(text=f"< {year - 1}", callback_data=f"{year_prefix}:{year - 1}"),
        InlineKeyboardButton(text=str(year), callback_data="noop"),
        InlineKeyboardButton(text=f"{year + 1} >", callback_data=f"{year_prefix}:{year + 1}"),
    ])
    rows.append([
        InlineKeyboardButton(text="Volver al menu", callback_data="main_menu"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
