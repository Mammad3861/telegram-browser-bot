from dataclasses import dataclass
from urllib.parse import urlparse

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from app.search.providers import SearchResult
from app.bot.i18n import text


SEARCH_ACTIONS = {"open", "refresh", "close"}


@dataclass(frozen=True)
class SearchCallback:
    session_id: str
    action: str
    index: int | None = None


def search_callback_data(
    session_id: str, action: str, index: int | None = None
) -> str:
    if action not in SEARCH_ACTIONS or (action == "open") != (index is not None):
        raise ValueError("Invalid search callback")
    value = (
        f"search:{session_id}:open:{index}"
        if action == "open"
        else f"search:{session_id}:{action}"
    )
    if len(value.encode("utf-8")) > 64:
        raise ValueError("Callback data exceeds Telegram's limit")
    return value


def parse_search_callback_data(value: str | None) -> SearchCallback | None:
    if not value:
        return None
    parts = value.split(":")
    if len(parts) not in {3, 4} or parts[0] != "search":
        return None
    session_id = parts[1]
    if len(session_id) != 8 or any(
        character not in "0123456789abcdef" for character in session_id.lower()
    ):
        return None
    action = parts[2]
    if action == "open" and len(parts) == 4 and parts[3].isdigit():
        return SearchCallback(session_id, action, int(parts[3]))
    if action in {"refresh", "close"} and len(parts) == 3:
        return SearchCallback(session_id, action)
    return None


def search_results_keyboard(
    session_id: str, result_count: int, language: str = "en"
) -> InlineKeyboardMarkup:
    number_buttons = [
        InlineKeyboardButton(
            text=str(index + 1),
            callback_data=search_callback_data(session_id, "open", index),
        )
        for index in range(result_count)
    ]
    controls = (
        text("search_again_button", language),
        text("close_button", language),
    )
    rows = [number_buttons] if number_buttons else []
    rows.append(
        [
            InlineKeyboardButton(
                text=controls[0],
                callback_data=search_callback_data(session_id, "refresh"),
            ),
            InlineKeyboardButton(
                text=controls[1],
                callback_data=search_callback_data(session_id, "close"),
            ),
        ]
    )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def format_search_results(
    query: str,
    results: tuple[SearchResult, ...] | list[SearchResult],
    heading: str,
    source_line: str | None = None,
    partial_line: str | None = None,
) -> str:
    lines = [heading]
    if source_line:
        lines.append(source_line)
    if partial_line:
        lines.append(partial_line)
    for index, result in enumerate(results, start=1):
        domain = urlparse(result.url).hostname or result.url
        lines.extend(["", f"{index}. {result.title}", f"   {domain}"])
        if result.snippet:
            snippet = " ".join(result.snippet.split())[:240]
            lines.append(f"   {snippet}")
    return "\n".join(lines)[:4000]
