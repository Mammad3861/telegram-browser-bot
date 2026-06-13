from dataclasses import dataclass

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.core.command_args import CommandArgumentError, parse_single_url_arg
from app.core.url_validation import URLValidationError, validate_url


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
    labels = (
        {
            "open": "🌐 باز کردن نشانی",
            "sessions": "🍪 نشست‌ها",
            "account": "⚙️ حساب",
            "help": "❓ راهنما",
            "search": "🔎 جست‌وجوی وب",
        }
        if language == "fa"
        else {
            "open": "🌐 Open URL",
            "sessions": "🍪 Sessions",
            "account": "⚙️ Account",
            "help": "❓ Help",
            "search": "🔎 Search Web",
        }
    )
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
    labels = (
        {
            "screenshot": "🖼 تصویر",
            "pdf": "🧾 PDF",
            "html": "📄 HTML",
            "rendered_html": "🌐 HTML رندرشده",
            "links": "🔗 پیوندها",
            "download": "⬇️ دانلود",
            "refresh": "🔄 تازه‌سازی",
            "cancel": "❌ لغو",
        }
        if language == "fa"
        else {
            "screenshot": "🖼 Screenshot",
            "pdf": "🧾 PDF",
            "html": "📄 HTML",
            "rendered_html": "🌐 Rendered HTML",
            "links": "🔗 Links",
            "download": "⬇️ Download",
            "refresh": "🔄 Refresh",
            "cancel": "❌ Cancel",
        }
    )
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
