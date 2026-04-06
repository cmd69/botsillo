import logging
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from app.db import get_user_by_chat_id

log = logging.getLogger(__name__)


def _user_label(event: TelegramObject) -> tuple[str, str]:
    """Extrae (chat_id, name) para logging."""
    if isinstance(event, Message) and event.from_user:
        u = event.from_user
        return str(event.chat.id), u.full_name or u.username or "?"
    if isinstance(event, CallbackQuery) and event.from_user:
        u = event.from_user
        cid = str(event.message.chat.id) if event.message else "?"
        return cid, u.full_name or u.username or "?"
    return "?", "unknown"


class AuthMiddleware(BaseMiddleware):
    """Autenticacion automatica por telegram_chat_id.

    Solo los usuarios con chat_id registrado en la tabla user de expensivo
    pueden interactuar con el bot. Sin excepciones.
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        cid, name = _user_label(event)

        if isinstance(event, Message):
            chat_id = event.chat.id
            msg_text = event.text or "[no text]"
            log.info("CHAT_ID [%s] %s: %s", cid, name, msg_text)
        elif isinstance(event, CallbackQuery):
            chat_id = event.message.chat.id if event.message else None
            log.info("CHAT_ID [%s] %s: callback %s", cid, name, event.data)
        else:
            return await handler(event, data)

        if chat_id is None:
            log.warning("CHAT_ID [%s] %s: no se pudo extraer chat_id", cid, name)
            return

        try:
            user = await get_user_by_chat_id(chat_id)
        except Exception:
            log.exception("CHAT_ID [%s] %s: error consultando DB", cid, name)
            if isinstance(event, Message):
                await event.answer("Error interno. Intentalo mas tarde.")
            elif isinstance(event, CallbackQuery):
                await event.answer("Error interno.", show_alert=True)
            return

        if not user:
            log.warning("CHAT_ID [%s] %s: NO registrado en expensivo", cid, name)
            if isinstance(event, Message):
                await event.answer(
                    "No tienes acceso a este bot.\n"
                    "Tu cuenta de Expensivo debe tener tu Telegram chat_id configurado."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("Sin acceso. Chat ID no registrado.", show_alert=True)
            return

        log.info("CHAT_ID [%s] %s: autenticado como '%s'", cid, name, user.username)
        data["user"] = user
        return await handler(event, data)
