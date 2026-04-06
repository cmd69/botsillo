"""Date picker en dos pasos: mes (grid 4x3) -> dia (grid 7 cols).

Mismo estilo visual que month_picker, con ↩️ Atras y ❌ Cancelar.
Cada flujo usa un prefix distinto para evitar colisiones de callback_data.
"""
import calendar
from datetime import date, timedelta

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

MONTHS_ES = [
    "Ene", "Feb", "Mar", "Abr", "May", "Jun",
    "Jul", "Ago", "Sep", "Oct", "Nov", "Dic",
]

DAYS_HEADER = ["Lu", "Ma", "Mi", "Ju", "Vi", "Sa", "Do"]


def month_step_kb(prefix: str, year: int | None = None) -> InlineKeyboardMarkup:
    """Grid 4x3 de meses + hoy/ayer + nav anyo + atras/cancelar."""
    if year is None:
        year = date.today().year

    today = date.today()
    yesterday = today - timedelta(days=1)

    rows: list[list[InlineKeyboardButton]] = []

    for row_start in range(0, 12, 4):
        row = []
        for i in range(row_start, row_start + 4):
            month_num = i + 1
            cb = f"{prefix}:m:{year}-{month_num:02d}"
            row.append(InlineKeyboardButton(text=MONTHS_ES[i], callback_data=cb))
        rows.append(row)

    rows.append([
        InlineKeyboardButton(text=f"< {year - 1}", callback_data=f"{prefix}:y:{year - 1}"),
        InlineKeyboardButton(text=str(year), callback_data="noop"),
        InlineKeyboardButton(text=f"{year + 1} >", callback_data=f"{prefix}:y:{year + 1}"),
    ])
    rows.append([
        InlineKeyboardButton(
            text=f"📅 Hoy ({today.strftime('%d/%m')})",
            callback_data=f"{prefix}:d:{today.isoformat()}",
        ),
        InlineKeyboardButton(
            text=f"📅 Ayer ({yesterday.strftime('%d/%m')})",
            callback_data=f"{prefix}:d:{yesterday.isoformat()}",
        ),
    ])
    rows.append([
        InlineKeyboardButton(text="↩️ Atras", callback_data="back"),
        InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def day_step_kb(prefix: str, year: int, month: int) -> InlineKeyboardMarkup:
    """Grid de dias del mes (7 cols, Lu-Do) + atras/cancelar."""
    rows: list[list[InlineKeyboardButton]] = []

    # Header dias semana
    rows.append([
        InlineKeyboardButton(text=d, callback_data="noop") for d in DAYS_HEADER
    ])

    # Dias del mes
    cal = calendar.Calendar(firstweekday=0)  # Lunes primero
    month_days = cal.monthdayscalendar(year, month)

    for week in month_days:
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data="noop"))
            else:
                cb = f"{prefix}:d:{year}-{month:02d}-{day:02d}"
                row.append(InlineKeyboardButton(text=str(day), callback_data=cb))
        rows.append(row)

    # Titulo mes
    month_label = f"{MONTHS_ES[month - 1]} {year}"
    rows.append([
        InlineKeyboardButton(text=month_label, callback_data="noop"),
    ])
    rows.append([
        InlineKeyboardButton(text="↩️ Atras", callback_data="back"),
        InlineKeyboardButton(text="❌ Cancelar", callback_data="cancel"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)
