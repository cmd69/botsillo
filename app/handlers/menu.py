from aiogram import F, Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message

from app import texts
from app.db import User
from app.keyboards.main_menu import main_menu_kb

router = Router(name="menu")


@router.message(Command("menu"))
async def cmd_menu(message: Message, user: User) -> None:
    await message.answer(texts.MENU_TITLE, reply_markup=main_menu_kb())


@router.callback_query(F.data == "main_menu")
async def cb_main_menu(callback: CallbackQuery, user: User) -> None:
    """Volver al menu principal desde cualquier flujo."""
    await callback.message.edit_text(texts.MENU_TITLE, reply_markup=main_menu_kb())
    await callback.answer()
