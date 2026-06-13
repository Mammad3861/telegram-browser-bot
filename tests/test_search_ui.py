import pytest

from app.search.ui import (
    parse_search_callback_data,
    search_callback_data,
    search_results_keyboard,
)


@pytest.mark.parametrize(
    ("value", "action", "index"),
    [
        ("search:abc12345:open:2", "open", 2),
        ("search:abc12345:refresh", "refresh", None),
        ("search:abc12345:close", "close", None),
    ],
)
def test_search_callback_parsing(value: str, action: str, index: int | None) -> None:
    parsed = parse_search_callback_data(value)

    assert parsed is not None
    assert parsed.action == action
    assert parsed.index == index


def test_search_callback_data_stays_within_telegram_limit() -> None:
    values = [
        search_callback_data("abc12345", "open", 4),
        search_callback_data("abc12345", "refresh"),
        search_callback_data("abc12345", "close"),
    ]

    assert all(len(value.encode("utf-8")) <= 64 for value in values)
    keyboard = search_results_keyboard("abc12345", 5)
    assert len(keyboard.inline_keyboard[0]) == 5


@pytest.mark.parametrize(
    "value",
    [None, "", "search:bad:refresh", "search:abc12345:open", "search:abc12345:open:x"],
)
def test_invalid_search_callback_data_is_rejected(value) -> None:
    assert parse_search_callback_data(value) is None

