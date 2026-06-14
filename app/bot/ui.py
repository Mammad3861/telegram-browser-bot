from dataclasses import dataclass

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.command_args import CommandArgumentError, parse_single_url_arg
from app.core.url_validation import URLValidationError, validate_url
from app.bot.i18n import text


URL_ACTIONS = {
    "screenshot",
    "pdf",
    "html",
    "rendered_html",
    "links",
    "download",
    "refresh",
    "cancel",
}


@dataclass(frozen=True)
class URLCallback:
    session_id: str
    action: str


def detect_plain_url(value: str | None) -> str | None:
    try:
        return validate_url(parse_single_url_arg(value))
    except (CommandArgumentError, URLValidationError):
        return None


def url_callback_data(session_id: str, action: str) -> str:
    if action not in URL_ACTIONS:
        raise ValueError("Unsupported URL action")
    value = f"url:{session_id}:{action}"
    if len(value.encode("utf-8")) > 64:
        raise ValueError("Callback data exceeds Telegram's limit")
    return value


def parse_url_callback_data(value: str | None) -> URLCallback | None:
    if not value:
        return None
    parts = value.split(":")
    if len(parts) != 3 or parts[0] != "url" or parts[2] not in URL_ACTIONS:
        return None
    session_id = parts[1]
    if len(session_id) != 8 or any(
        character not in "0123456789abcdef" for character in session_id.lower()
    ):
        return None
    return URLCallback(session_id=session_id, action=parts[2])


def menu_keyboard(language: str = "en") -> InlineKeyboardMarkup:
    labels = {
        "open": text("menu_open_url", language),
        "sessions": text("menu_sessions", language),
        "account": text("menu_account", language),
        "help": text("menu_help", language),
        "search": text("menu_search", language),
    }
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=labels["open"], callback_data="menu:open_url")],
            [
                InlineKeyboardButton(text=labels["sessions"], callback_data="menu:sessions"),
                InlineKeyboardButton(text=labels["account"], callback_data="menu:account"),
            ],
            [
                InlineKeyboardButton(text=labels["help"], callback_data="menu:help"),
                InlineKeyboardButton(text=labels["search"], callback_data="menu:search"),
            ],
        ]
    )


def url_action_keyboard(session_id: str, language: str = "en") -> InlineKeyboardMarkup:
    labels = {
        "screenshot": text("url_screenshot_button", language),
        "pdf": text("url_pdf_button", language),
        "html": text("url_html_button", language),
        "rendered_html": text("url_rendered_html_button", language),
        "links": text("url_links_button", language),
        "download": text("url_download_button", language),
        "refresh": text("url_refresh_button", language),
        "cancel": text("url_cancel_button", language),
    }
    button = lambda label, action: InlineKeyboardButton(
        text=label, callback_data=url_callback_data(session_id, action)
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [button(labels["screenshot"], "screenshot"), button(labels["pdf"], "pdf")],
            [button(labels["html"], "html"), button(labels["rendered_html"], "rendered_html")],
            [button(labels["links"], "links"), button(labels["download"], "download")],
            [button(labels["refresh"], "refresh"), button(labels["cancel"], "cancel")],
        ]
    )
