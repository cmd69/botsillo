import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand

from app.config import settings
from app.handlers import start
from app.middlewares.auth import AuthMiddleware

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger(__name__)


async def set_commands(bot: Bot) -> None:
    await bot.set_my_commands([
        BotCommand(command="start", description="Iniciar / vincular cuenta"),
        BotCommand(command="menu", description="Menu principal"),
    ])


async def main() -> None:
    bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    dp.include_router(start.router)

    await set_commands(bot)
    log.info("Botsillo arrancado — polling activo")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
