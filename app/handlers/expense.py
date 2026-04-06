import logging
from datetime import date
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.api_client import create_transaction, get_categories
from app.db import User
from app.keyboards.amount import amount_kb
from app.keyboards.categories import categories_kb
from app.keyboards.common import confirm_cancel_kb, empty_cancel_kb
from app.keyboards.date_picker import day_step_kb, month_step_kb
from app.keyboards.main_menu import main_menu_kb
from app.states import ExpenseFlow

router = Router(name="expense")
log = logging.getLogger(__name__)

PREFIX = "ed"  # expense date


def _roots(cats: list[dict]) -> list[dict]:
    return [c for c in cats if not c.get("parent_category_id")]


def _children(cats: list[dict], parent_id: str) -> list[dict]:
    return [c for c in cats if str(c.get("parent_category_id", "")) == parent_id]


def _cat_label(cat: dict) -> str:
    emoji = cat.get("emoji", "")
    return f"{emoji} {cat['name']}".strip() if emoji else cat["name"]


def _fmt_date(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


# --- Entrada ---

@router.callback_query(F.data == "menu:expense")
async def start_expense(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.clear()
    await state.update_data(user_id=str(user.id))

    cats = await get_categories(user.id)
    roots = _roots(cats)
    if not roots:
        await callback.message.edit_text(
            "No tienes categorias configuradas en Expensivo.",
            reply_markup=main_menu_kb(),
        )
        await callback.answer()
        return

    await state.update_data(all_categories=cats)
    await callback.message.edit_text(
        "Selecciona la categoria:", reply_markup=categories_kb(roots)
    )
    await state.set_state(ExpenseFlow.category)
    await callback.answer()


# --- Categoria ---

@router.callback_query(ExpenseFlow.category, F.data.startswith("cat:"))
async def select_category(callback: CallbackQuery, state: FSMContext) -> None:
    cat_id = callback.data.split(":", 1)[1]
    data = await state.get_data()
    cats = data.get("all_categories", [])
    cat = next((c for c in cats if str(c["id"]) == cat_id), None)

    await state.update_data(category_id=cat_id, category_name=_cat_label(cat) if cat else "?")

    children = _children(cats, cat_id)
    if children:
        await callback.message.edit_text(
            "Selecciona la subcategoria:", reply_markup=categories_kb(children, prefix="subcat")
        )
        await state.set_state(ExpenseFlow.subcategory)
    else:
        await callback.message.edit_text(
            "Selecciona el mes:", reply_markup=month_step_kb(PREFIX)
        )
        await state.set_state(ExpenseFlow.month)

    await callback.answer()


@router.callback_query(ExpenseFlow.category, F.data.startswith("catpage:"))
async def category_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split(":", 1)[1])
    data = await state.get_data()
    roots = _roots(data.get("all_categories", []))
    await callback.message.edit_reply_markup(reply_markup=categories_kb(roots, page))
    await callback.answer()


# --- Subcategoria ---

@router.callback_query(ExpenseFlow.subcategory, F.data.startswith("subcat:"))
async def select_subcategory(callback: CallbackQuery, state: FSMContext) -> None:
    subcat_id = callback.data.split(":", 1)[1]
    data = await state.get_data()
    cats = data.get("all_categories", [])
    subcat = next((c for c in cats if str(c["id"]) == subcat_id), None)

    if subcat:
        parent_name = data.get("category_name", "")
        full_name = f"{parent_name} > {_cat_label(subcat)}"
        await state.update_data(category_id=subcat_id, category_name=full_name)

    await callback.message.edit_text(
        "Selecciona el mes:", reply_markup=month_step_kb(PREFIX)
    )
    await state.set_state(ExpenseFlow.month)
    await callback.answer()


@router.callback_query(ExpenseFlow.subcategory, F.data.startswith("subcatpage:"))
async def subcategory_page(callback: CallbackQuery, state: FSMContext) -> None:
    page = int(callback.data.split(":", 1)[1])
    data = await state.get_data()
    parent_id = data.get("category_id", "")
    children = _children(data.get("all_categories", []), parent_id)
    await callback.message.edit_reply_markup(reply_markup=categories_kb(children, page, prefix="subcat"))
    await callback.answer()


# --- Fecha: mes ---

@router.callback_query(ExpenseFlow.month, F.data.startswith(f"{PREFIX}:m:"))
async def select_month(callback: CallbackQuery, state: FSMContext) -> None:
    ym = callback.data.split(":", 2)[2]  # YYYY-MM
    year, month = int(ym.split("-")[0]), int(ym.split("-")[1])
    await state.update_data(cal_year=year, cal_month=month)
    await callback.message.edit_text(
        "Selecciona el dia:", reply_markup=day_step_kb(PREFIX, year, month)
    )
    await state.set_state(ExpenseFlow.day)
    await callback.answer()


@router.callback_query(ExpenseFlow.month, F.data.startswith(f"{PREFIX}:y:"))
async def change_year(callback: CallbackQuery) -> None:
    year = int(callback.data.split(":", 2)[2])
    await callback.message.edit_reply_markup(reply_markup=month_step_kb(PREFIX, year))
    await callback.answer()


# --- Fecha: dia ---

@router.callback_query(ExpenseFlow.day, F.data.startswith(f"{PREFIX}:d:"))
async def select_day(callback: CallbackQuery, state: FSMContext) -> None:
    iso_date = callback.data.split(":", 2)[2]  # YYYY-MM-DD
    await state.update_data(selected_date=iso_date)
    await callback.message.edit_text(
        "Importe:\nEnvia un mensaje con el importe. Ej: 19.86",
        reply_markup=amount_kb(),
    )
    await state.set_state(ExpenseFlow.amount)
    await callback.answer()


# --- Importe (texto o boton rapido) ---

@router.callback_query(ExpenseFlow.amount, F.data.startswith("amt:"))
async def quick_amount(callback: CallbackQuery, state: FSMContext) -> None:
    amount = float(callback.data.split(":", 1)[1])
    await state.update_data(amount=amount)
    await callback.message.edit_text(
        "Descripcion:\nEnvia un mensaje con la descripcion.",
        reply_markup=empty_cancel_kb(),
    )
    await state.set_state(ExpenseFlow.description)
    await callback.answer()


@router.message(ExpenseFlow.amount)
async def enter_amount(message: Message, state: FSMContext) -> None:
    raw = message.text.strip().replace(",", ".")
    try:
        amount = float(raw)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer("Formato incorrecto. Ej: 19.86")
        return

    await state.update_data(amount=amount)
    await message.answer(
        "Descripcion:\nEnvia un mensaje con la descripcion.",
        reply_markup=empty_cancel_kb(),
    )
    await state.set_state(ExpenseFlow.description)


# --- Descripcion (texto o vacio) ---

@router.message(ExpenseFlow.description)
async def enter_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await _show_confirm(message, state)


@router.callback_query(ExpenseFlow.description, F.data == "skip")
async def skip_description(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(description="-")
    data = await state.get_data()
    await callback.message.edit_text(_confirm_text(data), reply_markup=confirm_cancel_kb(), parse_mode="HTML")
    await state.set_state(ExpenseFlow.confirm)
    await callback.answer()


async def _show_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await message.answer(_confirm_text(data), reply_markup=confirm_cancel_kb(), parse_mode="HTML")
    await state.set_state(ExpenseFlow.confirm)


def _confirm_text(data: dict) -> str:
    return (
        f"💸 <b>Nuevo gasto</b>\n\n"
        f"<b>Categoria:</b> {data['category_name']}\n"
        f"<b>Fecha:</b> {_fmt_date(data['selected_date'])}\n"
        f"<b>Importe:</b> {data['amount']}€\n"
        f"<b>Descripcion:</b> {data.get('description', '-')}\n\n"
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
        text = (
            f"✅ <b>Gasto guardado</b>\n\n"
            f"<b>Categoria:</b> {data['category_name']}\n"
            f"<b>Fecha:</b> {_fmt_date(data['selected_date'])}\n"
            f"<b>Importe:</b> {data['amount']}€\n"
            f"<b>Descripcion:</b> {data.get('description', '-')}"
        )
        await callback.message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")
    else:
        await callback.message.edit_text("❌ Error al guardar el gasto.", reply_markup=main_menu_kb())

    await state.clear()
    await callback.answer()


# --- Cancel: vuelve al menu ---

@router.callback_query(ExpenseFlow.category, F.data == "cancel")
@router.callback_query(ExpenseFlow.subcategory, F.data == "cancel")
@router.callback_query(ExpenseFlow.month, F.data == "cancel")
@router.callback_query(ExpenseFlow.day, F.data == "cancel")
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
    await state.clear()
    await callback.message.edit_text("Que quieres hacer?", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(ExpenseFlow.subcategory, F.data == "back")
async def back_from_subcategory(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    roots = _roots(data.get("all_categories", []))
    await callback.message.edit_text(
        "Selecciona la categoria:", reply_markup=categories_kb(roots)
    )
    await state.set_state(ExpenseFlow.category)
    await callback.answer()


@router.callback_query(ExpenseFlow.month, F.data == "back")
async def back_from_month(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    roots = _roots(data.get("all_categories", []))
    await callback.message.edit_text(
        "Selecciona la categoria:", reply_markup=categories_kb(roots)
    )
    await state.set_state(ExpenseFlow.category)
    await callback.answer()


@router.callback_query(ExpenseFlow.day, F.data == "back")
async def back_from_day(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Selecciona el mes:", reply_markup=month_step_kb(PREFIX)
    )
    await state.set_state(ExpenseFlow.month)
    await callback.answer()


# --- noop ---

@router.callback_query(F.data == "noop")
async def noop(callback: CallbackQuery) -> None:
    await callback.answer()
