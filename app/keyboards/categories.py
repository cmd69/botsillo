"""Teclado paginado de categorias. Grid 3x4 + navegacion."""
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.keyboards.common import back_cancel_row

COLS = 3
ROWS = 4
PAGE_SIZE = COLS * ROWS


def categories_kb(categories: list[dict], page: int = 0, prefix: str = "cat") -> InlineKeyboardMarkup:
    """Genera teclado paginado de categorias.

    Cada categoria es un dict con al menos 'id', 'name', 'emoji'.
    callback_data = '<prefix>:<id>'
    """
    total = len(categories)
    start = page * PAGE_SIZE
    end = min(start + PAGE_SIZE, total)
    page_items = categories[start:end]

    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []

    for cat in page_items:
        emoji = cat.get("emoji", "")
        label = f"{emoji} {cat['name']}" if emoji else cat["name"]
        current_row.append(
            InlineKeyboardButton(text=label, callback_data=f"{prefix}:{cat['id']}")
        )
        if len(current_row) == COLS:
            rows.append(current_row)
            current_row = []

    if current_row:
        rows.append(current_row)

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton(text="⬅️ Anterior", callback_data=f"{prefix}page:{page - 1}"))
    total_pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton(text="Siguiente ➡️", callback_data=f"{prefix}page:{page + 1}"))
    if nav_row:
        rows.append(nav_row)

    rows.append(back_cancel_row())
    return InlineKeyboardMarkup(inline_keyboard=rows)
