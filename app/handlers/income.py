import logging
from datetime import date
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.api_client import create_transaction
from app.db import User
from app.keyboards.amount import amount_kb
from app.keyboards.common import confirm_cancel_kb, empty_cancel_kb
from app.keyboards.date_picker import day_step_kb, month_step_kb
from app.keyboards.main_menu import main_menu_kb
from app.states import IncomeFlow

router = Router(name="income")
log = logging.getLogger(__name__)

PREFIX = "id"  # income date


def _fmt_date(iso: str) -> str:
    return date.fromisoformat(iso).strftime("%d/%m/%Y")


# --- Entrada ---

@router.callback_query(F.data == "menu:income")
async def start_income(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.clear()
    await state.update_data(user_id=str(user.id))
    await callback.message.edit_text(
        "Selecciona el mes:", reply_markup=month_step_kb(PREFIX)
    )
    await state.set_state(IncomeFlow.month)
    await callback.answer()


# --- Fecha: mes ---

@router.callback_query(IncomeFlow.month, F.data.startswith(f"{PREFIX}:m:"))
async def select_month(callback: CallbackQuery, state: FSMContext) -> None:
    ym = callback.data.split(":", 2)[2]
    year, month = int(ym.split("-")[0]), int(ym.split("-")[1])
    await state.update_data(cal_year=year, cal_month=month)
    await callback.message.edit_text(
        "Selecciona el dia:", reply_markup=day_step_kb(PREFIX, year, month)
    )
    await state.set_state(IncomeFlow.day)
    await callback.answer()


@router.callback_query(IncomeFlow.month, F.data.startswith(f"{PREFIX}:y:"))
async def change_year(callback: CallbackQuery) -> None:
    year = int(callback.data.split(":", 2)[2])
    await callback.message.edit_reply_markup(reply_markup=month_step_kb(PREFIX, year))
    await callback.answer()


@router.callback_query(IncomeFlow.month, F.data.startswith(f"{PREFIX}:d:"))
async def quick_date_from_month(callback: CallbackQuery, state: FSMContext) -> None:
    """Hoy/Ayer seleccionados desde el paso de mes."""
    iso_date = callback.data.split(":", 2)[2]
    await state.update_data(selected_date=iso_date)
    await callback.message.edit_text(
        "Importe:\nEnvia un mensaje con el importe. Ej: 19.86",
        reply_markup=amount_kb(),
    )
    await state.set_state(IncomeFlow.amount)
    await callback.answer()


# --- Fecha: dia ---

@router.callback_query(IncomeFlow.day, F.data.startswith(f"{PREFIX}:d:"))
async def select_day(callback: CallbackQuery, state: FSMContext) -> None:
    iso_date = callback.data.split(":", 2)[2]
    await state.update_data(selected_date=iso_date)
    await callback.message.edit_text(
        "Importe:\nEnvia un mensaje con el importe. Ej: 19.86",
        reply_markup=amount_kb(),
    )
    await state.set_state(IncomeFlow.amount)
    await callback.answer()


# --- Importe (texto o boton rapido) ---

@router.callback_query(IncomeFlow.amount, F.data.startswith("amt:"))
async def quick_amount(callback: CallbackQuery, state: FSMContext) -> None:
    amount = float(callback.data.split(":", 1)[1])
    await state.update_data(amount=amount)
    await callback.message.edit_text(
        "Descripcion:\nEnvia un mensaje con la descripcion.",
        reply_markup=empty_cancel_kb(),
    )
    await state.set_state(IncomeFlow.description)
    await callback.answer()


@router.message(IncomeFlow.amount)
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
    await state.set_state(IncomeFlow.description)


# --- Descripcion (texto o vacio) ---

@router.message(IncomeFlow.description)
async def enter_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await _show_confirm(message, state)


@router.callback_query(IncomeFlow.description, F.data == "skip")
async def skip_description(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(description="-")
    data = await state.get_data()
    await callback.message.edit_text(_confirm_text(data), reply_markup=confirm_cancel_kb(), parse_mode="HTML")
    await state.set_state(IncomeFlow.confirm)
    await callback.answer()


async def _show_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    await message.answer(_confirm_text(data), reply_markup=confirm_cancel_kb(), parse_mode="HTML")
    await state.set_state(IncomeFlow.confirm)


def _confirm_text(data: dict) -> str:
    return (
        f"💰 <b>Nuevo ingreso</b>\n\n"
        f"<b>Fecha:</b> {_fmt_date(data['selected_date'])}\n"
        f"<b>Importe:</b> {data['amount']}€\n"
        f"<b>Descripcion:</b> {data.get('description', '-')}\n\n"
        f"Confirmar?"
    )


# --- Confirmar ---

@router.callback_query(IncomeFlow.confirm, F.data == "confirm")
async def confirm_income(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    user_id = UUID(data["user_id"])
    tx_date = date.fromisoformat(data["selected_date"])

    result = await create_transaction(
        user_id=user_id,
        tx_type="income",
        amount=data["amount"],
        tx_date=tx_date,
        description=data.get("description"),
    )

    if result:
        text = (
            f"✅ <b>Ingreso guardado</b>\n\n"
            f"<b>Fecha:</b> {_fmt_date(data['selected_date'])}\n"
            f"<b>Importe:</b> {data['amount']}€\n"
            f"<b>Descripcion:</b> {data.get('description', '-')}"
        )
        await callback.message.edit_text(text, reply_markup=main_menu_kb(), parse_mode="HTML")
    else:
        await callback.message.edit_text("❌ Error al guardar el ingreso.", reply_markup=main_menu_kb())

    await state.clear()
    await callback.answer()


# --- Cancel: vuelve al menu ---

@router.callback_query(IncomeFlow.month, F.data == "cancel")
@router.callback_query(IncomeFlow.day, F.data == "cancel")
@router.callback_query(IncomeFlow.amount, F.data == "cancel")
@router.callback_query(IncomeFlow.description, F.data == "cancel")
@router.callback_query(IncomeFlow.confirm, F.data == "cancel")
async def cancel_income(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Cancelado.", reply_markup=main_menu_kb())
    await callback.answer()


# --- Back: vuelve al paso anterior ---

@router.callback_query(IncomeFlow.month, F.data == "back")
async def back_from_month(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Que quieres hacer?", reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(IncomeFlow.day, F.data == "back")
async def back_from_day(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Selecciona el mes:", reply_markup=month_step_kb(PREFIX)
    )
    await state.set_state(IncomeFlow.month)
    await callback.answer()


@router.callback_query(IncomeFlow.amount, F.data == "back")
async def back_from_amount(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Selecciona el mes:", reply_markup=month_step_kb(PREFIX)
    )
    await state.set_state(IncomeFlow.month)
    await callback.answer()


@router.callback_query(IncomeFlow.description, F.data == "back")
async def back_from_description(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        "Importe:\nEnvia un mensaje con el importe. Ej: 19.86",
        reply_markup=amount_kb(),
    )
    await state.set_state(IncomeFlow.amount)
    await callback.answer()
