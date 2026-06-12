import pytest

from app.bot.handlers import parse_access_target


def test_parse_access_target_with_note() -> None:
    assert parse_access_target("123456 test account") == (123456, "test account")


def test_parse_access_target_rejects_non_integer() -> None:
    with pytest.raises(ValueError, match="must be an integer"):
        parse_access_target("not-an-id")
