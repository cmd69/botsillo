from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app import texts
from app.api_client import get_categories
from app.category_utils import roots as root_categories
from app.db import User
from app.keyboards.categories import categories_kb
from app.keyboards.date_picker import month_step_kb
from app.keyboards.main_menu import expenses_menu_kb, main_menu_kb, portfolio_menu_kb
from app.states import ExpenseFlow, IncomeFlow

router = Router(name="menu")


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, state: FSMContext, user: User) -> None:
    await state.clear()
    await callback.message.edit_text(texts.MENU_TITLE, reply_markup=main_menu_kb())
    await callback.answer()


@router.callback_query(F.data == "menu:root_expenses")
async def cb_root_expenses(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "Seccion <b>Gastos</b>: registra movimientos o consulta tu actividad.",
        reply_markup=expenses_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.callback_query(F.data == "menu:root_portfolio")
async def cb_root_portfolio(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "<b>Portfolio</b>: consultar, transacciones de activos o movimientos de capital.",
        reply_markup=portfolio_menu_kb(),
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(Command("gasto"))
async def cmd_gasto(message: Message, state: FSMContext, user: User) -> None:
    await state.clear()
    await state.update_data(user_id=str(user.id))

    cats = await get_categories(user.id)
    roots = root_categories(cats)
    if not roots:
        await message.answer(
            "No tienes categorias configuradas en Expensivo.",
            reply_markup=main_menu_kb(),
        )
        return

    await state.update_data(all_categories=cats)
    await message.answer("Selecciona la categoria:", reply_markup=categories_kb(roots))
    await state.set_state(ExpenseFlow.category)


@router.message(Command("ingreso"))
async def cmd_ingreso(message: Message, state: FSMContext, user: User) -> None:
    await state.clear()
    await state.update_data(user_id=str(user.id))
    await message.answer("Selecciona el mes:", reply_markup=month_step_kb("id"))
    await state.set_state(IncomeFlow.month)


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery) -> None:
    """Botones decorativos de calendarios y pickers (titulo, dias vacios)."""
    await callback.answer()
