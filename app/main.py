import asyncio
from contextlib import asynccontextmanager, suppress

from aiogram import Bot
from fastapi import FastAPI

from app.api.routes import router
from app.bot.dispatcher import create_dispatcher
from app.config import get_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    polling_task: asyncio.Task[None] | None = None
    bot: Bot | None = None

    if settings.telegram_bot_token:
        bot = Bot(token=settings.telegram_bot_token)
        polling_task = asyncio.create_task(create_dispatcher().start_polling(bot))

    yield

    if polling_task:
        polling_task.cancel()
        with suppress(asyncio.CancelledError):
            await polling_task
    if bot:
        await bot.session.close()


app = FastAPI(title="Telegram Browser Bot", version="0.9.2", lifespan=lifespan)
app.include_router(router)
