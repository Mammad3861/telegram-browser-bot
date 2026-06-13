import json

from app.core.preference_store import (
    get_user_language,
    load_preferences,
    set_user_language,
)


def test_preference_save_and_load(tmp_path) -> None:
    path = tmp_path / "preferences" / "user_preferences.json"

    saved = set_user_language(path, 123, "fa")
    loaded = load_preferences(path)

    assert saved.user_id == 123
    assert saved.language == "fa"
    assert loaded == [saved]
    assert not path.with_suffix(".json.tmp").exists()


def test_language_persists_after_store_reload(tmp_path) -> None:
    path = tmp_path / "user_preferences.json"
    set_user_language(path, 123, "fa")

    assert get_user_language(path, 123) == "fa"
    assert get_user_language(path, 999) == "en"


def test_corrupted_preferences_fall_back_to_default(tmp_path) -> None:
    path = tmp_path / "user_preferences.json"
    path.write_text("{broken", encoding="utf-8")

    assert load_preferences(path) == []
    assert get_user_language(path, 123) == "en"


def test_preference_json_contains_required_fields(tmp_path) -> None:
    path = tmp_path / "user_preferences.json"
    set_user_language(path, 123, "en")

    item = json.loads(path.read_text(encoding="utf-8"))["users"][0]
    assert set(item) == {"user_id", "language", "updated_at"}

