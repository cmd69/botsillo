import logging

from aiogram import Router
from aiogram.filters import CommandStart, CommandObject
from aiogram.types import Message

from app.auth import decode_link_token
from app.db import get_user_by_chat_id, link_telegram

router = Router(name="start")
log = logging.getLogger(__name__)


@router.message(CommandStart(deep_link=True))
async def cmd_start_link(message: Message, command: CommandObject) -> None:
    """Maneja /start <token> para vinculacion de cuenta."""
    token = command.args
    if not token:
        return await cmd_start_plain(message)

    user_id = decode_link_token(token)
    if not user_id:
        await message.answer("El enlace de vinculacion es invalido o ha expirado.")
        return

    # Comprobar si este chat ya esta vinculado
    existing = await get_user_by_chat_id(message.chat.id)
    if existing:
        await message.answer("Este chat ya esta vinculado a una cuenta de Expensivo.")
        return

    ok = await link_telegram(user_id, message.chat.id)
    if ok:
        log.info("Usuario %s vinculado a chat %s", user_id, message.chat.id)
        await message.answer(
            "Cuenta vinculada correctamente!\n\n"
            "Usa /menu para ver las opciones disponibles."
        )
    else:
        await message.answer("No se pudo vincular la cuenta. Intentalo de nuevo.")


@router.message(CommandStart())
async def cmd_start_plain(message: Message) -> None:
    """Maneja /start sin argumentos."""
    user = await get_user_by_chat_id(message.chat.id)
    if user:
        await message.answer(
            f"Hola {user.username}! Usa /menu para ver las opciones."
        )
    else:
        await message.answer(
            "Hola! Soy Botsillo, el bot de Expensivo.\n\n"
            "Para usar este bot necesitas vincular tu cuenta desde la app de Expensivo "
            "(Settings > Vincular Telegram)."
        )
