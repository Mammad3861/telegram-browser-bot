import pytest

from app.bot.i18n import (
    TEXTS,
    clear_language_preferences,
    get_language,
    set_language,
    text,
)


@pytest.fixture(autouse=True)
def reset_preferences() -> None:
    clear_language_preferences()


def test_language_preference_defaults_to_english() -> None:
    assert get_language(123) == "en"
    assert set_language(123, "fa") == "fa"
    assert get_language(123) == "fa"


def test_rejects_unsupported_language() -> None:
    with pytest.raises(ValueError):
        set_language(123, "de")


def test_text_lookup_supports_english_and_persian() -> None:
    assert text("menu", "en") == TEXTS["en"]["menu"]
    assert text("menu", "fa") == TEXTS["fa"]["menu"]


def test_missing_persian_key_falls_back_to_english(monkeypatch) -> None:
    monkeypatch.delitem(TEXTS["fa"], "help")

    assert text("help", "fa") == TEXTS["en"]["help"]


def test_search_messages_exist_and_fallback_to_english(monkeypatch) -> None:
    assert "/search" in text("search_usage", "en")
    assert text("search_unavailable", "fa") == TEXTS["fa"]["search_unavailable"]
    monkeypatch.delitem(TEXTS["fa"], "search_expired")
    assert text("search_expired", "fa") == TEXTS["en"]["search_expired"]
