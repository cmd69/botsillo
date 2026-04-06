from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app import texts
from app.config import settings
from app.db import User
from app.keyboards.main_menu import main_menu_kb

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, user: User) -> None:
    await message.answer(
        texts.start_welcome_html(settings.EXPENSIVE_WEB_URL),
        reply_markup=main_menu_kb(),
        parse_mode="HTML",
    )
