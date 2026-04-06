import logging
from datetime import date
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import texts
from app.api_client import create_transaction
from app.db import User
from app.keyboards.calendar import build_calendar, calendar_filter, process_calendar
from app.keyboards.common import confirm_cancel_kb, skip_cancel_kb
from app.states import IncomeFlow

router = Router(name="income")
log = logging.getLogger(__name__)

CAL_ID = 2  # calendar_id distinto al de expense


# --- Entrada al flujo ---

@router.callback_query(F.data == "menu:income")
async def start_income(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.clear()
    await state.update_data(user_id=str(user.id))
    markup, step_text = build_calendar(calendar_id=CAL_ID)
    await callback.message.edit_text(
        f"Selecciona {step_text}:", reply_markup=markup
    )
    await state.set_state(IncomeFlow.date)
    await callback.answer()


# --- Fecha (DetailedTelegramCalendar) ---

@router.callback_query(IncomeFlow.date, calendar_filter(calendar_id=CAL_ID))
async def process_income_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    selected_date, markup, step_text = process_calendar(callback.data, calendar_id=CAL_ID)

    if selected_date:
        await state.update_data(
            selected_date=selected_date.isoformat(),
            year_month=selected_date.strftime("%Y-%m"),
        )
        await callback.message.edit_text(texts.INCOME_ENTER_AMOUNT)
        await state.set_state(IncomeFlow.amount)
    elif markup:
        await callback.message.edit_text(
            f"Selecciona {step_text}:", reply_markup=markup
        )

    await callback.answer()


# --- Importe ---

@router.message(IncomeFlow.amount)
async def enter_amount(message: Message, state: FSMContext) -> None:
    text = message.text.strip().replace(",", ".")
    try:
        amount = float(text)
        if amount <= 0:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer("Introduce un importe valido (ej: 1500.00)")
        return

    await state.update_data(amount=amount)
    await message.answer(
        texts.INCOME_ENTER_DESC, reply_markup=skip_cancel_kb()
    )
    await state.set_state(IncomeFlow.description)


# --- Descripcion ---

@router.message(IncomeFlow.description)
async def enter_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=message.text.strip())
    await _show_confirm(message, state)


@router.callback_query(IncomeFlow.description, F.data == "skip")
async def skip_description(callback: CallbackQuery, state: FSMContext) -> None:
    await state.update_data(description="-")
    await _show_confirm_cb(callback, state)


async def _show_confirm(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    text = texts.INCOME_CONFIRM.format(
        month=data["year_month"],
        day=data["selected_date"],
        amount=data["amount"],
        description=data.get("description", "-"),
    )
    await message.answer(text, reply_markup=confirm_cancel_kb())
    await state.set_state(IncomeFlow.confirm)


async def _show_confirm_cb(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    text = texts.INCOME_CONFIRM.format(
        month=data["year_month"],
        day=data["selected_date"],
        amount=data["amount"],
        description=data.get("description", "-"),
    )
    await callback.message.edit_text(text, reply_markup=confirm_cancel_kb())
    await state.set_state(IncomeFlow.confirm)
    await callback.answer()


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
        await callback.message.edit_text(texts.INCOME_SAVED)
    else:
        await callback.message.edit_text(texts.INCOME_ERROR)

    await state.clear()
    await callback.answer()


# --- Cancel ---

@router.callback_query(IncomeFlow.date, F.data == "cancel")
@router.callback_query(IncomeFlow.amount, F.data == "cancel")
@router.callback_query(IncomeFlow.description, F.data == "cancel")
@router.callback_query(IncomeFlow.confirm, F.data == "cancel")
async def cancel_income(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(texts.CANCELLED)
    await callback.answer()
