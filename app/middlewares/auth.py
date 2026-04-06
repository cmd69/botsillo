import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.db import get_user_by_chat_id

log = logging.getLogger(__name__)


def _user_label(event: TelegramObject) -> str:
    """Extrae [chat_id] Name para logging."""
    if isinstance(event, Message) and event.from_user:
        u = event.from_user
        name = u.full_name or u.username or "?"
        return f"[{event.chat.id}] {name}"
    if isinstance(event, CallbackQuery) and event.from_user:
        u = event.from_user
        chat_id = event.message.chat.id if event.message else "?"
        name = u.full_name or u.username or "?"
        return f"[{chat_id}] {name}"
    return "[?] unknown"


class AuthMiddleware(BaseMiddleware):
    """Autenticacion automatica por telegram_chat_id.

    Solo los usuarios con chat_id registrado en la tabla user de expensivo
    pueden interactuar con el bot. Sin excepciones (ni /start).
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        label = _user_label(event)

        # Extraer chat_id y texto del mensaje
        if isinstance(event, Message):
            chat_id = event.chat.id
            msg_text = event.text or "[no text]"
            log.info("%s: %s", label, msg_text)
        elif isinstance(event, CallbackQuery):
            chat_id = event.message.chat.id if event.message else None
            log.info("%s: callback %s", label, event.data)
        else:
            return await handler(event, data)

        if chat_id is None:
            log.warning("%s: no se pudo extraer chat_id", label)
            return

        # Buscar usuario por chat_id
        try:
            user = await get_user_by_chat_id(chat_id)
        except Exception:
            log.exception("%s: error consultando DB", label)
            if isinstance(event, Message):
                await event.answer("Error interno. Intentalo mas tarde.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Error interno.", show_alert=True)
            return

        if not user:
            log.warning("%s: chat_id NO registrado en expensivo", label)
            if isinstance(event, Message):
                await event.answer(
                    "No tienes acceso a este bot.\n"
                    "Tu cuenta de Expensivo debe tener tu Telegram chat_id configurado."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("Sin acceso. Chat ID no registrado.", show_alert=True)
            return

        log.info("%s: autenticado como '%s'", label, user.username)
        data["user"] = user
        return await handler(event, data)
