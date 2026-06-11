from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from app.core.url_validation import URLValidationError
from app.fetchers.http_fetcher import FetchError, HttpFetcher
from app.fetchers.link_extractor import LinkExtractor

router = Router()

HELP_TEXT = (
    "Commands:\n"
    "/fetch <url> - fetch a web page\n"
    "/links <url> - list links from a web page\n"
    "/help - show this help"
)


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    await message.answer("Telegram Browser Bot is ready.\n\n" + HELP_TEXT)


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("fetch"))
async def fetch_handler(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Usage: /fetch <url>")
        return

    try:
        async with HttpFetcher() as fetcher:
            response = await fetcher.fetch(command.args.strip())
        body = response.text[:3500]
        await message.answer(f"Status: {response.status_code}\n\n{body}")
    except (URLValidationError, FetchError) as exc:
        await message.answer(f"Error: {exc}")


@router.message(Command("links"))
async def links_handler(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer("Usage: /links <url>")
        return

    try:
        url = command.args.strip()
        async with HttpFetcher() as fetcher:
            response = await fetcher.fetch(url)
        links = LinkExtractor.extract(response.text, str(response.url))
        if not links:
            await message.answer("No links found.")
            return
        text = "\n".join(links[:50])
        await message.answer(text[:4000])
    except (URLValidationError, FetchError) as exc:
        await message.answer(f"Error: {exc}")
