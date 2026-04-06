import logging
from datetime import date
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.api_client import create_transaction, get_categories
from app.db import User
from app.keyboards.calendar import build_calendar, calendar_filter, process_calendar
from app.keyboards.categories import categories_kb
from app.keyboards.common import confirm_cancel_kb, skip_cancel_kb
from app.keyboards.main_menu import main_menu_kb
from app.states import ExpenseFlow

router = Router(name="expense")
log = logging.getLogger(__name__)

CAL_ID = 1


# --- Entrada ---

@router.callback_query(F.data == "menu:expense")
async def start_expense(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.clear()
    await state.update_data(user_id=str(user.id))

    # Cargar categorias al inicio
    cats = await get_categories(user.id)
    if not cats:
        await callback.message.edit_text(
            "No tienes categorias configuradas en Expensivo.",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return

    await state.update_data(categories=cats)
    await callback.message.edit_text(
        "Selecciona la categoria:", reply_markup=categories_kb(cats)
    )
    await state.set_state(ExpenseFlow.category)
    await callback.answer()


# --- Categoria ---

@router.callback_query(ExpenseFlow.category, F.data.startswith("cat:"))
async def select_category(callback: CallbackQuery, state: FSMContext) -> None:
    cat_id = callback.data.split(":", 1)[1]
    data = await state.get_data()
    cats = data.get("categories", [])
    cat = next((c for c in cats if str(c["id"]) == cat_id), None)
    cat_name = f"{cat.get('emoji', '')} {cat['name']}".strip() if cat else "?"

    await state.update_data(category_id=cat_id, category_name=cat_name)

    markup, step_text = build_calendar(calendar_id=CAL_ID)
    await callback.message.edit_text(f"Selecciona {step_text}:", reply_markup=markup)
    await state.set_state(ExpenseFlow.date)
    await callback.answer()


@router.callback_query(ExpenseFlow.category, F.data.startswith("catpage:"))
async def category_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split(":", 1)[1])
    data = await state.get_data()
    await callback.message.edit_reply_markup(reply_markup=categories_kb(data.get("categories", []), page))
    await callback.answer()


# --- Fecha ---

@router.callback_query(ExpenseFlow.date, calendar_filter(calendar_id=CAL_ID))
async def process_expense_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    selected_date, markup, step_text = process_calendar(callback.data, calendar_id=CAL_ID)

    if selected_date:
        await state.update_data(selected_date=selected_date.isoformat())
        await callback.message.edit_text("Importe:")
        await state.set_state(ExpenseFlow.amount)
    elif markup:
        await callback.message.edit_text(f"Selecciona {step_text}:", reply_markup=markup)

    await callback.answer()


# --- Importe (texto) ---

@router.message(ExpenseFlow.amount)
async def enter_amount(message: Message, state: FSMContext) -> None:
    raw = message.text.strip().replace(",", ".")
    try:
        amount = float(raw)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer("Formato incorrecto. Ejemplo: 10.5")
        return

    await state.update_data(amount=amount)
    await message.answer("Descripcion:", reply_markup=skip_cancel_kb())
    await state.set_state(ExpenseFlow.description)


# --- Descripcion (texto o saltar) ---

@router.message(ExpenseFlow.description)
async def enter_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await _show_confirm(message, state)


@router.callback_query(ExpenseFlow.description, F.data == "skip")
async def skip_description(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(description="-")
    data = await state.get_data()
    await callback.message.edit_text(_confirm_text(data), reply_markup=confirm_cancel_kb())
    await state.set_state(ExpenseFlow.confirm)
    await callback.answer()


async def _show_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await message.answer(_confirm_text(data), reply_markup=confirm_cancel_kb())
    await state.set_state(ExpenseFlow.confirm)


def _confirm_text(data: dict) -> str:
    return (
        f"Nuevo gasto:\n\n"
        f"Categoria: {data['category_name']}\n"
        f"Fecha: {data['selected_date']}\n"
        f"Importe: {data['amount']}\n"
        f"Descripcion: {data.get('description', '-')}\n\n"
        f"Confirmar?"
    )


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
        await callback.message.edit_text("Gasto guardado correctamente", reply_markup=main_menu_kb())
    else:
        await callback.message.edit_text("Error al guardar el gasto.", reply_markup=main_menu_kb())

    await state.clear()
    await callback.answer()


# --- Cancel: vuelve al menu ---

@router.callback_query(ExpenseFlow.category, F.data == "cancel")
@router.callback_query(ExpenseFlow.date, F.data == "cancel")
@router.callback_query(ExpenseFlow.amount, F.data == "cancel")
@router.callback_query(ExpenseFlow.description, F.data == "cancel")
@router.callback_query(ExpenseFlow.confirm, F.data == "cancel")
async def cancel_expense(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Cancelado.", reply_markup=main_menu_kb())
    await callback.answer()


# --- Back: vuelve al paso anterior ---

@router.callback_query(ExpenseFlow.category, F.data == "back")
async def back_from_category(callback: CallbackQuery, state: FSMContext) -> None:
    """Desde categorias -> menu principal."""
    await state.clear()
    await callback.message.edit_text("Que quieres hacer?", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(ExpenseFlow.date, F.data == "back")
async def back_from_date(callback: CallbackQuery, state: FSMContext) -> None:
    """Desde fecha -> categorias."""
    data = await state.get_data()
    await callback.message.edit_text(
        "Selecciona la categoria:", reply_markup=categories_kb(data.get("categories", []))
    )
    await state.set_state(ExpenseFlow.category)
    await callback.answer()


# --- noop ---

@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()
