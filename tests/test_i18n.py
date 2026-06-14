import pytest

from app.config import Settings
from app.core.bot_text_store import set_bot_text

from app.bot.i18n import (
    TEXTS,
    bot_text,
    get_language,
    set_language,
    text,
)


def test_language_preference_defaults_to_english(tmp_path) -> None:
    path = tmp_path / "preferences.json"
    assert get_language(123, path) == "en"
    assert set_language(123, "fa", path) == "fa"
    assert get_language(123, path) == "fa"


def test_rejects_unsupported_language(tmp_path) -> None:
    with pytest.raises(ValueError):
        set_language(123, "de", tmp_path / "preferences.json")


def test_text_lookup_supports_english_and_persian() -> None:
    assert text("menu", "en") == TEXTS["en"]["menu"]
    assert text("menu", "fa") == TEXTS["fa"]["menu"]


def test_all_english_keys_have_persian_equivalents() -> None:
    assert set(TEXTS["en"]) == set(TEXTS["fa"])


def test_missing_persian_key_falls_back_to_english(monkeypatch) -> None:
    monkeypatch.delitem(TEXTS["fa"], "help")

    assert text("help", "fa") == TEXTS["en"]["help"]


def test_search_messages_exist_and_fallback_to_english(monkeypatch) -> None:
    assert "/search" in text("search_usage", "en")
    assert text("search_unavailable", "fa") == TEXTS["fa"]["search_unavailable"]
    assert "direct URL" in text("search_unavailable", "en")
    assert "نشانی مستقیم" in text("search_unavailable", "fa")
    assert "Brave" in text("search_source", "en", provider="Brave")
    assert "منبع" in text("search_source", "fa", provider="Brave")
    monkeypatch.delitem(TEXTS["fa"], "search_expired")
    assert text("search_expired", "fa") == TEXTS["en"]["search_expired"]


def test_provider_message_falls_back_to_english(monkeypatch) -> None:
    monkeypatch.delitem(TEXTS["fa"], "search_misconfigured")

    assert text("search_misconfigured", "fa") == TEXTS["en"][
        "search_misconfigured"
    ]


def test_editable_bot_text_overrides_and_falls_back(tmp_path, monkeypatch) -> None:
    path = tmp_path / "bot_texts.json"
    settings = Settings(_env_file=None, bot_texts_path=str(path))
    monkeypatch.setattr("app.bot.i18n.get_settings", lambda: settings)
    set_bot_text(path, "welcome", "en", "Custom welcome", 3000)

    assert bot_text("welcome", "en") == "Custom welcome"
    assert bot_text("help", "en") == TEXTS["en"]["help"]


@pytest.mark.parametrize(
    "key",
    [
        "texts_overview",
        "text_updated",
        "text_reset",
        "text_preview",
        "text_invalid_key",
        "text_invalid_language",
        "text_too_long",
        "admin_required",
    ],
)
def test_admin_text_flow_has_persian_translations(key: str) -> None:
    assert key in TEXTS["fa"]
    assert TEXTS["fa"][key] != TEXTS["en"][key]


def test_persisted_language_is_used_by_menu_builder(tmp_path) -> None:
    from app.bot.ui import menu_keyboard

    path = tmp_path / "preferences.json"
    set_language(123, "fa", path)
    language = get_language(123, path)
    labels = [
        button.text
        for row in menu_keyboard(language).inline_keyboard
        for button in row
    ]

    assert text("menu_new_url", "fa") in labels
    assert text("menu_search", "fa") in labels


def test_admin_text_translation_falls_back_to_english(monkeypatch) -> None:
    monkeypatch.delitem(TEXTS["fa"], "text_updated")

    assert text("text_updated", "fa", key="help", language="fa") == (
        "Updated help/fa."
    )
