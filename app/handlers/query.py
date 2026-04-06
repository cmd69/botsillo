import logging
from datetime import date as date_type

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from app.api_client import get_summary, get_transactions
from app.db import User
from app.keyboards.main_menu import main_menu_kb
from app.keyboards.month_picker import month_picker_kb
from app.states import QueryFlow

router = Router(name="query")
log = logging.getLogger(__name__)

SUMMARY_PREFIX = "sm"


def _category_emoji_display(raw) -> str:
    """Evita 'None' en pantalla cuando la API devuelve null o falta emoji."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return "-"
    return str(raw).strip()


def _summary_text(year_month: str, data: dict) -> str:
    num_expenses = data.get("count", 0)
    return (
        f"📊 Resumen de {year_month}:\n\n"
        f"💸 Gastos: {data['total_expenses']}€\n"
        f"💰 Ingresos: {data['total_income']}€\n"
        f"🏦 Ahorro: {data['balance']}€\n"
        f"🔢 Num. gastos: {num_expenses}"
    )


def _detail_kb(year_month: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="💸 Ver gastos", callback_data=f"qlist:expense:{year_month}"),
            InlineKeyboardButton(text="💰 Ver ingresos", callback_data=f"qlist:income:{year_month}"),
        ],
        [InlineKeyboardButton(text="↩️ Atras", callback_data="q:back_months")],
    ])


def _list_back_kb(year_month: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="↩️ Atras", callback_data=f"q:back_summary:{year_month}")],
    ])


# --- Entrada: elegir mes ---

@router.callback_query(F.data == "menu:query")
async def start_query(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.clear()
    await state.update_data(user_id=str(user.id))
    await callback.message.edit_text(
        "Selecciona el mes:", reply_markup=month_picker_kb(prefix=SUMMARY_PREFIX)
    )
    await state.set_state(QueryFlow.month)
    await callback.answer()


@router.callback_query(QueryFlow.month, F.data.startswith(f"{SUMMARY_PREFIX}_year:"))
async def query_change_year(callback: CallbackQuery) -> None:
    year = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup(
        reply_markup=month_picker_kb(year, prefix=SUMMARY_PREFIX)
    )
    await callback.answer()


# --- Resumen del mes ---

@router.callback_query(QueryFlow.month, F.data.startswith(f"{SUMMARY_PREFIX}:"))
async def show_summary(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    year_month = callback.data.split(":")[1]
    await state.update_data(year_month=year_month)

    data = await get_summary(user.id, year_month)

    if not data:
        await callback.message.edit_text(
            "No hay transacciones para este periodo.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Atras", callback_data="q:back_months")],
            ]),
        )
        await state.set_state(QueryFlow.detail)
        await callback.answer()
        return

    await callback.message.edit_text(
        _summary_text(year_month, data), reply_markup=_detail_kb(year_month)
    )
    await state.set_state(QueryFlow.detail)
    await callback.answer()


# --- Listas de gastos/ingresos ---

@router.callback_query(QueryFlow.detail, F.data.startswith("qlist:"))
async def show_list(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    parts = callback.data.split(":")
    tx_type = parts[1]
    year_month = parts[2]

    txs = await get_transactions(user.id, year_month=year_month)
    filtered = [t for t in txs if t["type"] == tx_type]
    filtered.sort(key=lambda t: (t.get("date") or "", str(t.get("id", ""))))

    if not filtered:
        emoji = "💸" if tx_type == "expense" else "💰"
        label = "gastos" if tx_type == "expense" else "ingresos"
        await callback.message.edit_text(
            f"{emoji} No hay {label} en {year_month}.",
            reply_markup=_list_back_kb(year_month),
        )
        await callback.answer()
        return

    emoji = "💸" if tx_type == "expense" else "💰"
    label = "Gastos" if tx_type == "expense" else "Ingresos"
    lines = [f"{emoji} {label} de {year_month}:\n"]

    for tx in filtered:
        cat_emoji = _category_emoji_display(tx.get("category_emoji"))
        cat_name = tx.get("category_name", "")
        desc = tx.get("description", "")
        amount = tx["amount"]
        date_str = tx["date"]
        try:
            day = date_type.fromisoformat(date_str).strftime("%d")
        except (ValueError, TypeError):
            day = date_str

        cat_label = f"{cat_emoji} {cat_name}".strip() if cat_name else desc or "-"
        lines.append(f"  <b>{day}</b>  {cat_label}  {amount}€")

    await callback.message.edit_text(
        "\n".join(lines), reply_markup=_list_back_kb(year_month), parse_mode="HTML"
    )
    await callback.answer()


# --- Navegacion atras ---

@router.callback_query(QueryFlow.detail, F.data == "q:back_months")
async def back_to_months(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Selecciona el mes:", reply_markup=month_picker_kb(prefix=SUMMARY_PREFIX)
    )
    await state.set_state(QueryFlow.month)
    await callback.answer()


@router.callback_query(QueryFlow.detail, F.data.startswith("q:back_summary:"))
async def back_to_summary(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    year_month = callback.data.split(":")[2]
    data = await get_summary(user.id, year_month)

    if not data:
        await callback.message.edit_text(
            "No hay transacciones para este periodo.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Atras", callback_data="q:back_months")],
            ]),
        )
        await callback.answer()
        return

    await callback.message.edit_text(
        _summary_text(year_month, data), reply_markup=_detail_kb(year_month)
    )
    await callback.answer()


# --- Cancel ---

@router.callback_query(QueryFlow.month, F.data == "cancel")
@router.callback_query(QueryFlow.detail, F.data == "cancel")
async def cancel_query(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Cancelado.", reply_markup=main_menu_kb())
    await callback.answer()


# --- Ultimos 10 ---

@router.callback_query(F.data == "menu:recent")
async def show_recent(callback: CallbackQuery, user: User) -> None:
    data = await get_transactions(user.id, limit=10)

    if not data:
        await callback.message.edit_text(
            "No hay transacciones.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="↩️ Atras", callback_data="main_menu")],
            ]),
        )
        await callback.answer()
        return

    lines = ["📋 Ultimas transacciones:\n"]
    for tx in data:
        emoji = _category_emoji_display(tx.get("category_emoji"))
        cat = tx.get("category_name", "")
        desc = tx.get("description", "")
        amount = tx["amount"]
        tx_type = tx["type"]
        sign = "💸" if tx_type == "expense" else "💰"
        date_str = tx["date"]

        try:
            fmt_date = date_type.fromisoformat(date_str).strftime("%d/%m/%Y")
        except (ValueError, TypeError):
            fmt_date = date_str

        label = f"{emoji} {cat}".strip() if cat else desc or tx_type
        lines.append(f"  {sign} {fmt_date}  {amount}€  {label}")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="↩️ Atras", callback_data="main_menu")],
        ]),
    )
    await callback.answer()
