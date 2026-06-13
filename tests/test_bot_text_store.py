import pytest

from app.core.bot_text_store import (
    BotTextValidationError,
    get_bot_text,
    load_bot_texts,
    reset_bot_text,
    set_bot_text,
)


def test_text_set_get_and_reset(tmp_path) -> None:
    path = tmp_path / "texts" / "bot_texts.json"
    set_bot_text(path, "welcome", "en", "Custom welcome", 3000)

    assert get_bot_text(path, "welcome", "en") == "Custom welcome"
    assert reset_bot_text(path, "welcome", "en")
    assert get_bot_text(path, "welcome", "en") is None


def test_text_falls_back_when_override_missing(tmp_path) -> None:
    assert get_bot_text(tmp_path / "missing.json", "help", "fa") is None


@pytest.mark.parametrize(
    ("key", "language"),
    [("unknown", "en"), ("welcome", "de")],
)
def test_invalid_key_or_language_is_rejected(tmp_path, key, language) -> None:
    with pytest.raises(BotTextValidationError):
        set_bot_text(tmp_path / "texts.json", key, language, "value", 3000)


def test_text_max_length_is_enforced(tmp_path) -> None:
    with pytest.raises(BotTextValidationError, match="at most 5"):
        set_bot_text(tmp_path / "texts.json", "help", "en", "123456", 5)


def test_corrupted_text_json_falls_back_to_defaults(tmp_path) -> None:
    path = tmp_path / "bot_texts.json"
    path.write_text("not json", encoding="utf-8")

    assert load_bot_texts(path) == {}
    assert get_bot_text(path, "about", "en") is None


def test_reset_all_languages_for_key(tmp_path) -> None:
    path = tmp_path / "bot_texts.json"
    set_bot_text(path, "welcome", "en", "Hello", 3000)
    set_bot_text(path, "welcome", "fa", "سلام", 3000)

    assert reset_bot_text(path, "welcome")
    assert get_bot_text(path, "welcome", "en") is None
    assert get_bot_text(path, "welcome", "fa") is None

