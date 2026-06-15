from cryptography.fernet import Fernet

from app.core.browser_tab_state import load_tab_storage_state, save_tab_storage_state


def test_storage_state_save_and_load_is_encrypted(tmp_path) -> None:
    key = Fernet.generate_key().decode("ascii")
    state = {
        "cookies": [{"name": "consent", "value": "yes", "domain": "example.com"}],
        "origins": [{"origin": "https://example.com", "localStorage": []}],
    }

    assert save_tab_storage_state(123, "abc12345", state, tmp_path, key)
    saved = (tmp_path / "123" / "abc12345.json").read_text(encoding="utf-8")

    assert "consent" not in saved
    assert "yes" not in saved
    assert load_tab_storage_state(123, "abc12345", tmp_path, key) == state


def test_storage_state_is_skipped_without_encryption_key(tmp_path) -> None:
    assert not save_tab_storage_state(123, "abc12345", {"cookies": []}, tmp_path, "")
    assert load_tab_storage_state(123, "abc12345", tmp_path, "") is None
