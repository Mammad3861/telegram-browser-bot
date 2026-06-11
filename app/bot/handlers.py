from pathlib import Path

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile, Message

from app.config import get_settings, parse_telegram_ids
from app.core.access_control import is_admin, is_allowed_user
from app.core.storage import StorageError
from app.core.url_validation import URLValidationError
from app.fetchers.http_fetcher import FetchError, HttpFetcher
from app.fetchers.html_export import save_html
from app.fetchers.link_extractor import LinkExtractor

router = Router()

HELP_TEXT = (
    "Commands:\n"
    "/fetch <url> - fetch a web page\n"
    "/links <url> - list links from a web page\n"
    "/html <url> - export page HTML\n"
    "/whoami - show your Telegram ID\n"
    "/help - show this help"
)

ACCESS_DENIED = "Access denied. Ask the bot owner for access."


def get_user_id(message: Message) -> int | None:
    return message.from_user.id if message.from_user else None


async def reject_unless_allowed(message: Message) -> bool:
    user_id = get_user_id(message)
    if user_id is None or not is_allowed_user(user_id):
        await message.answer(ACCESS_DENIED)
        return True
    return False


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    await message.answer("Telegram Browser Bot is ready.\n\n" + HELP_TEXT)


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(HELP_TEXT)


@router.message(Command("whoami"))
async def whoami_handler(message: Message) -> None:
    user_id = get_user_id(message)
    await message.answer(f"Your Telegram ID: {user_id}" if user_id else "User ID unavailable")


@router.message(Command("access"))
async def access_handler(message: Message) -> None:
    user_id = get_user_id(message)
    if user_id is None or not is_admin(user_id):
        await message.answer(ACCESS_DENIED)
        return
    settings = get_settings()
    admins = sorted(parse_telegram_ids(settings.admin_telegram_ids))
    allowed = sorted(parse_telegram_ids(settings.allowed_telegram_ids))
    allowed_text = ", ".join(map(str, allowed)) if allowed else "admins only"
    await message.answer(
        f"Admins: {', '.join(map(str, admins)) or 'none'}\nAllowed users: {allowed_text}"
    )


@router.message(Command("fetch"))
async def fetch_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
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
    if await reject_unless_allowed(message):
        return
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


@router.message(Command("html"))
async def html_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    if not command.args:
        await message.answer("Usage: /html <url>")
        return

    settings = get_settings()
    try:
        async with HttpFetcher(max_response_bytes=0) as fetcher:
            response = await fetcher.fetch(command.args.strip())
        output_path = save_html(
            response.content,
            str(response.url),
            Path(settings.downloads_dir),
            settings.max_html_size_mb,
            settings.min_free_disk_mb,
        )
        await message.answer_document(FSInputFile(output_path))
    except (URLValidationError, FetchError, StorageError, OSError) as exc:
        await message.answer(f"Error: {exc}")
