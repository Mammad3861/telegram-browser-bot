import pytest

from app.bot.handlers import HELP_TEXT
from app.bot.i18n import text
from app.bot.ui import (
    URL_ACTIONS,
    detect_plain_url,
    parse_url_callback_data,
    url_callback_data,
)


def test_callback_data_round_trip() -> None:
    parsed = parse_url_callback_data("url:abc12345:screenshot")

    assert parsed is not None
    assert parsed.session_id == "abc12345"
    assert parsed.action == "screenshot"


@pytest.mark.parametrize("action", sorted(URL_ACTIONS))
def test_callback_data_stays_within_telegram_limit(action: str) -> None:
    value = url_callback_data("a1b2c3d4", action)

    assert len(value.encode("utf-8")) <= 64
    assert parse_url_callback_data(value) is not None


@pytest.mark.parametrize(
    "value", [None, "", "url:missing", "other:abc12345:pdf", "url:abc12345:unknown"]
)
def test_rejects_invalid_callback_data(value) -> None:
    assert parse_url_callback_data(value) is None


def test_plain_url_detection_accepts_single_public_url() -> None:
    assert detect_plain_url(" https://example.com/path ") == "https://example.com/path"


@pytest.mark.parametrize(
    "value",
    [
        "hello",
        "https://example.com https://example.org",
        "https://example.com\nhttps://example.org",
        "http://localhost/private",
        "file:///tmp/data",
    ],
)
def test_plain_url_detection_rejects_invalid_input(value: str) -> None:
    assert detect_plain_url(value) is None


def test_help_text_does_not_include_secrets() -> None:
    assert "TELEGRAM_BOT_TOKEN" not in HELP_TEXT
    assert "COOKIE_ENCRYPTION_KEY" not in HELP_TEXT
    assert "/menu" in HELP_TEXT
    assert "/language" in HELP_TEXT


def test_about_text_contains_version_and_runtime_without_secrets() -> None:
    about = text(
        "about",
        "en",
        version="1.4.1-alpha.1",
        runtime_target="Linux/Ubuntu 24.04 or Docker",
    )

    assert "Telegram Browser Bot" in about
    assert "1.4.1-alpha.1" in about
    assert "Linux/Ubuntu 24.04 or Docker" in about
    assert "TOKEN" not in about
