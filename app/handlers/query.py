import logging
from uuid import UUID

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

import httpx

from app import texts
from app.auth import create_bot_token
from app.config import settings
from app.db import User
from app.keyboards.calendar import month_picker_kb

router = Router(name="query")
log = logging.getLogger(__name__)

SUMMARY_PREFIX = "sm"  # summary_month


def _headers(user_id: UUID) -> dict:
    return {"Authorization": f"Bearer {create_bot_token(user_id)}"}


async def _api_get(path: str, user_id: UUID, params: dict | None = None) -> dict | list | None:
    async with httpx.AsyncClient(base_url=settings.API_BASE_URL, timeout=10.0) as client:
        try:
            resp = await client.get(path, headers=_headers(user_id), params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError:
            log.exception("Error en API GET %s", path)
            return None


_back_kb = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Volver al menu", callback_data="main_menu")],
])


# --- Resumen del mes ---

@router.callback_query(F.data == "menu:summary")
async def start_summary(callback: CallbackQuery, user: User) -> None:
    await callback.message.edit_text(
        "Selecciona el mes para ver el resumen:",
        reply_markup=month_picker_kb(prefix=SUMMARY_PREFIX),
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{SUMMARY_PREFIX}:"))
async def show_summary(callback: CallbackQuery, user: User) -> None:
    year_month = callback.data.split(":")[1]
    data = await _api_get("/api/v1/transactions/summary", user.id, {"year_month": year_month})

    if not data:
        await callback.message.edit_text(texts.NO_TRANSACTIONS, reply_markup=_back_kb)
        await callback.answer()
        return

    text = (
        f"{texts.SUMMARY_TITLE.format(month=year_month)}\n\n"
        f"{texts.SUMMARY_BODY.format(expenses=data['total_expenses'], income=data['total_income'], balance=data['balance'])}"
    )
    await callback.message.edit_text(text, reply_markup=_back_kb)
    await callback.answer()


@router.callback_query(F.data.startswith(f"{SUMMARY_PREFIX}_year:"))
async def summary_change_year(callback: CallbackQuery) -> None:
    year = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup(
        reply_markup=month_picker_kb(year, prefix=SUMMARY_PREFIX)
    )
    await callback.answer()


# --- Ultimos 10 ---

@router.callback_query(F.data == "menu:recent")
async def show_recent(callback: CallbackQuery, user: User) -> None:
    data = await _api_get("/api/v1/transactions/", user.id, {"limit": 10})

    if not data:
        await callback.message.edit_text(texts.NO_TRANSACTIONS, reply_markup=_back_kb)
        await callback.answer()
        return

    lines = ["Ultimas transacciones:\n"]
    for tx in data:
        emoji = tx.get("category_emoji", "")
        cat = tx.get("category_name", "")
        desc = tx.get("description", "")
        amount = tx["amount"]
        tx_type = tx["type"]
        sign = "-" if tx_type == "expense" else "+"
        date_str = tx["date"]

        label = f"{emoji} {cat}" if cat else desc or tx_type
        lines.append(f"  {date_str}  {sign}{amount:.2f}  {label.strip()}")

    await callback.message.edit_text("\n".join(lines), reply_markup=_back_kb)
    await callback.answer()
