"""Teclados inline para seleccion de mes y dia."""
from datetime import date, timedelta

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.keyboards.common import back_cancel_row

MONTHS_ES = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]


def month_picker_kb(year: int | None = None) -> InlineKeyboardMarkup:
    """Teclado 4x3 con los meses del anyo. callback_data = 'month:YYYY-MM'."""
    if year is None:
        year = date.today().year

    rows: list[list[InlineKeyboardButton]] = []
    for row_start in range(0, 12, 4):
        row = []
        for i in range(row_start, row_start + 4):
            month_num = i + 1
            label = MONTHS_ES[i]
            cb = f"month:{year}-{month_num:02d}"
            row.append(InlineKeyboardButton(text=label, callback_data=cb))
        rows.append(row)

    # Navegacion de anyo
    rows.append([
        InlineKeyboardButton(text=f"< {year - 1}", callback_data=f"year:{year - 1}"),
        InlineKeyboardButton(text=str(year), callback_data="noop"),
        InlineKeyboardButton(text=f"{year + 1} >", callback_data=f"year:{year + 1}"),
    ])
    rows.append(back_cancel_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)


def day_picker_kb(year: int, month: int) -> InlineKeyboardMarkup:
    """Teclado con dias del mes en grid 7 columnas (L-D). callback_data = 'day:DD'."""
    first = date(year, month, 1)
    # Calcular ultimo dia del mes
    if month == 12:
        last_day = 31
    else:
        last_day = (date(year, month + 1, 1) - timedelta(days=1)).day

    # Header dias de la semana
    dow_labels = ["L", "M", "X", "J", "V", "S", "D"]
    rows: list[list[InlineKeyboardButton]] = [
        [InlineKeyboardButton(text=d, callback_data="noop") for d in dow_labels]
    ]

    # Offset del primer dia (lunes=0)
    offset = first.weekday()
    current_row: list[InlineKeyboardButton] = []

    # Espacios vacios antes del dia 1
    for _ in range(offset):
        current_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))

    for day in range(1, last_day + 1):
        current_row.append(
            InlineKeyboardButton(text=str(day), callback_data=f"day:{day:02d}")
        )
        if len(current_row) == 7:
            rows.append(current_row)
            current_row = []

    # Rellenar ultima fila
    while len(current_row) > 0 and len(current_row) < 7:
        current_row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
    if current_row:
        rows.append(current_row)

    rows.append(back_cancel_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
