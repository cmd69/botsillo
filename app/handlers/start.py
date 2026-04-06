from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.db import User

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message, user: User) -> None:
    """Saludo inicial. El middleware ya verifico que el usuario existe."""
    await message.answer(
        f"Hola {user.username}! Usa /menu para ver las opciones."
    )
