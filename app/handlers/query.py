import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery

from app.api_client import get_summary, get_transactions
from app.db import User
from app.keyboards.common import back_menu_kb
from app.keyboards.month_picker import month_picker_kb

router = Router(name="query")
log = logging.getLogger(__name__)

SUMMARY_PREFIX = "sm"


# --- Resumen del mes ---

@router.callback_query(F.data == "menu:summary")
async def start_summary(callback: CallbackQuery, user: User) -> None:
    await callback.message.edit_text(
        "Selecciona el mes:", reply_markup=month_picker_kb(prefix=SUMMARY_PREFIX)
    )
    await callback.answer()


@router.callback_query(F.data.startswith(f"{SUMMARY_PREFIX}:"))
async def show_summary(callback: CallbackQuery, user: User) -> None:
    year_month = callback.data.split(":")[1]
    data = await get_summary(user.id, year_month)

    if not data:
        await callback.message.edit_text(
            "No hay transacciones para este periodo.", reply_markup=back_menu_kb()
        )
        await callback.answer()
        return

    text = (
        f"Resumen de {year_month}:\n\n"
        f"Gastos: {data['total_expenses']}\n"
        f"Ingresos: {data['total_income']}\n"
        f"Balance: {data['balance']}"
    )
    await callback.message.edit_text(text, reply_markup=back_menu_kb())
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
    data = await get_transactions(user.id, limit=10)

    if not data:
        await callback.message.edit_text(
            "No hay transacciones.", reply_markup=back_menu_kb()
        )
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
        lines.append(f"  {date_str}  {sign}{amount}  {label.strip()}")

    await callback.message.edit_text("\n".join(lines), reply_markup=back_menu_kb())
    await callback.answer()
