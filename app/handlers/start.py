from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app import texts
from app.db import User
from app.keyboards.main_menu import main_menu_kb

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, user: User) -> None:
    await message.answer(texts.MENU_TITLE, reply_markup=main_menu_kb())
