import logging
from datetime import date
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import texts
from app.api_client import create_transaction
from app.db import User
from app.keyboards.calendar import day_picker_kb, month_picker_kb
from app.keyboards.common import confirm_cancel_kb, skip_cancel_kb
from app.states import IncomeFlow

router = Router(name="income")
log = logging.getLogger(__name__)


# --- Entrada al flujo ---

@router.callback_query(F.data == "menu:income")
async def start_income(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.clear()
    await state.update_data(user_id=str(user.id))
    await callback.message.edit_text(
        texts.INCOME_SELECT_MONTH, reply_markup=month_picker_kb()
    )
    await state.set_state(IncomeFlow.month)
    await callback.answer()


# --- Mes ---

@router.callback_query(IncomeFlow.month, F.data.startswith("month:"))
async def select_month(callback: CallbackQuery, state: FSMContext) -> None:
    year_month = callback.data.split(":")[1]
    await state.update_data(year_month=year_month)

    year, month = map(int, year_month.split("-"))
    await callback.message.edit_text(
        texts.INCOME_SELECT_DAY, reply_markup=day_picker_kb(year, month)
    )
    await state.set_state(IncomeFlow.day)
    await callback.answer()


@router.callback_query(IncomeFlow.month, F.data.startswith("year:"))
async def change_year(callback: CallbackQuery) -> None:
    year = int(callback.data.split(":")[1])
    await callback.message.edit_reply_markup(reply_markup=month_picker_kb(year))
    await callback.answer()


# --- Dia ---

@router.callback_query(IncomeFlow.day, F.data.startswith("day:"))
async def select_day(callback: CallbackQuery, state: FSMContext) -> None:
    day = int(callback.data.split(":")[1])
    await state.update_data(day=day)
    await callback.message.edit_text(
        texts.INCOME_ENTER_AMOUNT, reply_markup=skip_cancel_kb()
    )
    await state.set_state(IncomeFlow.amount)
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
        day=data["day"],
        amount=data["amount"],
        description=data.get("description", "-"),
    )
    await message.answer(text, reply_markup=confirm_cancel_kb())
    await state.set_state(IncomeFlow.confirm)


async def _show_confirm_cb(callback: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    text = texts.INCOME_CONFIRM.format(
        month=data["year_month"],
        day=data["day"],
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
    year, month = map(int, data["year_month"].split("-"))
    day = data["day"]
    tx_date = date(year, month, day)

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


# --- Cancel / Back ---

@router.callback_query(IncomeFlow.month, F.data == "cancel")
@router.callback_query(IncomeFlow.day, F.data == "cancel")
@router.callback_query(IncomeFlow.amount, F.data == "cancel")
@router.callback_query(IncomeFlow.description, F.data == "cancel")
@router.callback_query(IncomeFlow.confirm, F.data == "cancel")
async def cancel_income(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(texts.CANCELLED)
    await callback.answer()


@router.callback_query(IncomeFlow.day, F.data == "back")
async def back_to_month(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.message.edit_text(
        texts.INCOME_SELECT_MONTH, reply_markup=month_picker_kb()
    )
    await state.set_state(IncomeFlow.month)
    await callback.answer()
