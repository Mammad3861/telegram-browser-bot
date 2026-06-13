import pytest

from app.bot.handlers import (
    localized_bot_text_error,
    parse_access_target,
    parse_set_text_args,
)
from app.core.bot_text_store import BotTextValidationError


def test_parse_access_target_with_note() -> None:
    assert parse_access_target("123456 test account") == (123456, "test account")


def test_parse_access_target_rejects_non_integer() -> None:
    with pytest.raises(ValueError, match="must be an integer"):
        parse_access_target("not-an-id")


def test_parse_set_text_preserves_text_body() -> None:
    assert parse_set_text_args("help fa متن راهنما") == (
        "help",
        "fa",
        "متن راهنما",
    )


def test_bot_text_validation_error_is_localized_to_persian() -> None:
    error = BotTextValidationError("Language must be en or fa", "invalid_language")

    message = localized_bot_text_error(error, "fa", 3000)

    assert "زبان نامعتبر" in message


def test_text_too_long_error_uses_configured_limit() -> None:
    error = BotTextValidationError("too long", "text_too_long")

    assert "42" in localized_bot_text_error(error, "en", 42)
