import asyncio
import logging
from contextlib import asynccontextmanager, suppress

from aiogram import Bot
from fastapi import FastAPI

from app.api.routes import router
from app.bot.dispatcher import create_dispatcher
from app.bot.commands import register_bot_commands
from app.config import get_settings
from app.core.config_validation import ensure_startup_directories, validate_startup_config
from app.version import APP_VERSION


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = validate_startup_config(get_settings())
    ensure_startup_directories(settings)
    polling_task: asyncio.Task[None] | None = None
    bot: Bot | None = None

    if settings.telegram_bot_token:
        bot = Bot(token=settings.telegram_bot_token)
        await register_bot_commands(bot, settings)
        polling_task = asyncio.create_task(create_dispatcher().start_polling(bot))
        logger.info("Telegram bot polling started")
    else:
        logger.warning(
            "TELEGRAM_BOT_TOKEN is not configured; API started with bot polling disabled"
        )

    if settings.enable_cookie_import and not settings.cookie_encryption_key:
        logger.warning(
            "COOKIE_ENCRYPTION_KEY is not configured; cookie import is disabled"
        )

    yield

    if polling_task:
        polling_task.cancel()
        with suppress(asyncio.CancelledError):
            await polling_task
    if bot:
        await bot.session.close()


app = FastAPI(title="Telegram Browser Bot", version=APP_VERSION, lifespan=lifespan)
app.include_router(router)
