import asyncio
import logging

from aiogram import Bot, Dispatcher, Router
from aiogram.types import BotCommand, ErrorEvent

from app.config import settings
from app.handlers import start, menu, portfolio, expense, income, query
from app.middlewares.auth import AuthMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)

error_router = Router(name="errors")


@error_router.error()
async def global_error_handler(event: ErrorEvent) -> bool:
    """Captura errores no manejados y los loguea sin crashear."""
    log.error(
        "Error procesando update %s: %s",
        event.update.update_id if event.update else "?",
        event.exception,
        exc_info=event.exception,
    )
    # Intentar notificar al usuario
    try:
        update = event.update
        if update.message:
            await update.message.answer("Ha ocurrido un error. Intentalo de nuevo.")
        elif update.callback_query:
            await update.callback_query.answer("Error interno.", show_alert=True)
    except Exception:
        pass
    return True


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="start", description="Menu principal"),
        BotCommand(command="gasto", description="Registrar gasto"),
        BotCommand(command="ingreso", description="Registrar ingreso"),
    ])


async def main() -> None:
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    dp.include_router(error_router)
    dp.include_router(start.router)
    dp.include_router(menu.router)
    dp.include_router(portfolio.router)
    dp.include_router(expense.router)
    dp.include_router(income.router)
    dp.include_router(query.router)

    await set_commands(bot)
    log.info("Botsillo arrancado — polling activo")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
