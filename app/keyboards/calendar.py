"""Wrapper sobre python-telegram-bot-calendar para aiogram v3.

Usa DetailedTelegramCalendar para seleccion completa de fecha (year -> month -> day).
Convierte el markup dict de la libreria a InlineKeyboardMarkup de aiogram.
"""
import json
from datetime import date

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP

# Re-exportar para uso en handlers
__all__ = ["DetailedTelegramCalendar", "LSTEP", "build_calendar", "process_calendar", "calendar_filter", "to_aiogram_markup"]

# Textos en espanol para los pasos
LSTEP_ES = {
    "y": "el anyo",
    "m": "el mes",
    "d": "el dia",
}


def to_aiogram_markup(calendar_markup) -> InlineKeyboardMarkup | None:
    """Convierte el markup de telegram-bot-calendar a InlineKeyboardMarkup de aiogram."""
    if calendar_markup is None:
        return None

    if isinstance(calendar_markup, str):
        data = json.loads(calendar_markup)
    elif isinstance(calendar_markup, dict):
        data = calendar_markup
    else:
        data = calendar_markup

    rows = []
    for row in data.get("inline_keyboard", []):
        buttons = []
        for btn in row:
            buttons.append(InlineKeyboardButton(
                text=str(btn["text"]),
                callback_data=str(btn.get("callback_data", "noop")),
            ))
        rows.append(buttons)
    return InlineKeyboardMarkup(inline_keyboard=rows)


def build_calendar(calendar_id: int = 0, min_date: date | None = None, max_date: date | None = None) -> tuple[InlineKeyboardMarkup, str]:
    """Construye un calendario y retorna (markup_aiogram, step_text_es)."""
    kwargs = {"calendar_id": calendar_id}
    if min_date:
        kwargs["min_date"] = min_date
    if max_date:
        kwargs["max_date"] = max_date

    calendar, step = DetailedTelegramCalendar(**kwargs).build()
    markup = to_aiogram_markup(calendar)
    step_text = LSTEP_ES.get(LSTEP[step], LSTEP[step])
    return markup, step_text


def process_calendar(callback_data: str, calendar_id: int = 0, min_date: date | None = None, max_date: date | None = None) -> tuple[date | None, InlineKeyboardMarkup | None, str | None]:
    """Procesa un callback del calendario.

    Retorna (selected_date, next_markup, step_text_es).
    - Si selected_date no es None, el usuario selecciono una fecha completa.
    - Si next_markup no es None, hay que actualizar el teclado.
    """
    kwargs = {"calendar_id": calendar_id}
    if min_date:
        kwargs["min_date"] = min_date
    if max_date:
        kwargs["max_date"] = max_date

    result, key, step = DetailedTelegramCalendar(**kwargs).process(callback_data)
    markup = to_aiogram_markup(key)
    step_text = LSTEP_ES.get(LSTEP[step], LSTEP[step]) if step is not None else None
    return result, markup, step_text


def calendar_filter(calendar_id: int = 0):
    """Retorna un callable para filtrar callbacks del calendario en aiogram v3."""
    return DetailedTelegramCalendar.func(calendar_id=calendar_id)
