from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, TelegramObject

from app.db import get_user_by_chat_id


class AuthMiddleware(BaseMiddleware):
    """Verifica que el usuario tiene cuenta vinculada.

    Inyecta 'user' en el handler data si esta vinculado.
    Deja pasar /start sin verificar (para permitir vinculacion).
    """

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        # Extraer chat_id segun tipo de evento
        if isinstance(event, Message):
            # Dejar pasar /start sin auth
            if event.text and event.text.startswith("/start"):
                return await handler(event, data)
            chat_id = event.chat.id
        elif isinstance(event, CallbackQuery):
            chat_id = event.message.chat.id if event.message else None
        else:
            return await handler(event, data)

        if chat_id is None:
            return

        user = await get_user_by_chat_id(chat_id)
        if not user:
            if isinstance(event, Message):
                await event.answer(
                    "No tienes una cuenta vinculada.\n"
                    "Vincula tu cuenta desde Expensivo (Settings > Vincular Telegram)."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer("Cuenta no vinculada.", show_alert=True)
            return

        data["user"] = user
        return await handler(event, data)
