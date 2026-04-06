from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

router = Router(name="start")


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    """Maneja /start y /start <token> para vinculacion."""
    args = message.text.split(maxsplit=1)

    if len(args) > 1:
        # /start <token> — flujo de vinculacion (se implementa en paso 3)
        await message.answer("Vinculacion pendiente de implementar.")
        return

    await message.answer(
        "Hola! Soy Botsillo, el bot de Expensivo.\n\n"
        "Para usar este bot necesitas vincular tu cuenta desde la app de Expensivo "
        "(Settings > Vincular Telegram)."
    )
