import logging
from datetime import date
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import texts
from app.api_client import create_transaction, get_categories
from app.db import User
from app.keyboards.calendar import build_calendar, calendar_filter, process_calendar
from app.keyboards.categories import categories_kb
from app.keyboards.common import confirm_cancel_kb, skip_cancel_kb
from app.states import ExpenseFlow

router = Router(name="expense")
log = logging.getLogger(__name__)

CAL_ID = 1  # calendar_id para distinguir del income


# --- Entrada al flujo ---

@router.callback_query(F.data == "menu:expense")
async def start_expense(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.clear()
    await state.update_data(user_id=str(user.id))
    markup, step_text = build_calendar(calendar_id=CAL_ID)
    await callback.message.edit_text(
        f"Selecciona {step_text}:", reply_markup=markup
    )
    await state.set_state(ExpenseFlow.date)
    await callback.answer()


# --- Fecha (DetailedTelegramCalendar) ---

@router.callback_query(ExpenseFlow.date, calendar_filter(calendar_id=CAL_ID))
async def process_expense_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    selected_date, markup, step_text = process_calendar(callback.data, calendar_id=CAL_ID)

    if selected_date:
        # Fecha seleccionada — guardar y pasar a categorias
        await state.update_data(
            selected_date=selected_date.isoformat(),
            year_month=selected_date.strftime("%Y-%m"),
        )
        # Cargar categorias
        data = await state.get_data()
        user_id = UUID(data["user_id"])
        cats = await get_categories(user_id)
        expense_cats = [c for c in cats if c.get("type") == "expense" and not c.get("parent_category_id")]
        await state.update_data(categories=expense_cats)

        await callback.message.edit_text(
            texts.EXPENSE_SELECT_CATEGORY, reply_markup=categories_kb(expense_cats)
        )
        await state.set_state(ExpenseFlow.category)
    elif markup:
        await callback.message.edit_text(
            f"Selecciona {step_text}:", reply_markup=markup
        )

    await callback.answer()


# --- Categoria ---

@router.callback_query(ExpenseFlow.category, F.data.startswith("cat:"))
async def select_category(callback: CallbackQuery, state: FSMContext) -> None:
    cat_id = callback.data.split(":")[1]
    data = await state.get_data()

    cats = data.get("categories", [])
    cat_name = next((c["name"] for c in cats if str(c["id"]) == cat_id), "?")
    cat_emoji = next((c.get("emoji", "") for c in cats if str(c["id"]) == cat_id), "")

    await state.update_data(category_id=cat_id, category_name=f"{cat_emoji} {cat_name}".strip())
    await callback.message.edit_text(texts.EXPENSE_ENTER_AMOUNT)
    await state.set_state(ExpenseFlow.amount)
    await callback.answer()


@router.callback_query(ExpenseFlow.category, F.data.startswith("catpage:"))
async def category_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split(":")[1])
    data = await state.get_data()
    cats = data.get("categories", [])
    await callback.message.edit_reply_markup(reply_markup=categories_kb(cats, page))
    await callback.answer()


# --- Importe ---

@router.message(ExpenseFlow.amount)
async def enter_amount(message: Message, state: FSMContext) -> None:
    text = message.text.strip().replace(",", ".")
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer("Introduce un importe valido (ej: 12.50)")
        return

    await state.update_data(amount=amount)
    await message.answer(
        texts.EXPENSE_ENTER_DESC, reply_markup=skip_cancel_kb()
    )
    await state.set_state(ExpenseFlow.description)


# --- Descripcion ---

@router.message(ExpenseFlow.description)
async def enter_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await _show_confirm(message, state)


@router.callback_query(ExpenseFlow.description, F.data == "skip")
async def skip_description(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(description="-")
    await _show_confirm_cb(callback, state)


async def _show_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    text = texts.EXPENSE_CONFIRM.format(
        month=data["year_month"],
        category=data["category_name"],
        day=data["selected_date"],
        amount=data["amount"],
        description=data.get("description", "-"),
    )
    await message.answer(text, reply_markup=confirm_cancel_kb())
    await state.set_state(ExpenseFlow.confirm)


async def _show_confirm_cb(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    text = texts.EXPENSE_CONFIRM.format(
        month=data["year_month"],
        category=data["category_name"],
        day=data["selected_date"],
        amount=data["amount"],
        description=data.get("description", "-"),
    )
    await callback.message.edit_text(text, reply_markup=confirm_cancel_kb())
    await state.set_state(ExpenseFlow.confirm)
    await callback.answer()


# --- Confirmar ---

@router.callback_query(ExpenseFlow.confirm, F.data == "confirm")
async def confirm_expense(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    user_id = UUID(data["user_id"])
    tx_date = date.fromisoformat(data["selected_date"])

    result = await create_transaction(
        user_id=user_id,
        tx_type="expense",
        amount=data["amount"],
        tx_date=tx_date,
        category_id=UUID(data["category_id"]),
        description=data.get("description"),
    )

    if result:
        await callback.message.edit_text(texts.EXPENSE_SAVED)
    else:
        await callback.message.edit_text(texts.EXPENSE_ERROR)

    await state.clear()
    await callback.answer()


# --- Cancel / Back ---

@router.callback_query(ExpenseFlow.date, F.data == "cancel")
@router.callback_query(ExpenseFlow.category, F.data == "cancel")
@router.callback_query(ExpenseFlow.amount, F.data == "cancel")
@router.callback_query(ExpenseFlow.description, F.data == "cancel")
@router.callback_query(ExpenseFlow.confirm, F.data == "cancel")
async def cancel_expense(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(texts.CANCELLED)
    await callback.answer()


@router.callback_query(ExpenseFlow.category, F.data == "back")
async def back_to_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    markup, step_text = build_calendar(calendar_id=CAL_ID)
    await callback.message.edit_text(
        f"Selecciona {step_text}:", reply_markup=markup
    )
    await state.set_state(ExpenseFlow.date)
    await callback.answer()


# Ignorar noop (botones decorativos)
@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()
