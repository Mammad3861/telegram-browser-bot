import json

from cryptography.fernet import Fernet

from app.config import Settings
from app.core import session_store


def configure_store(monkeypatch, tmp_path) -> Settings:
    settings = Settings(
        cookie_encryption_key=Fernet.generate_key().decode(),
        session_storage_dir=str(tmp_path / "sessions"),
    )
    monkeypatch.setattr(session_store, "get_settings", lambda: settings)
    return settings


def test_session_save_load_and_delete(monkeypatch, tmp_path) -> None:
    configure_store(monkeypatch, tmp_path)
    cookies_json = json.dumps(
        [{"name": "session", "value": "secret-value", "domain": "example.com"}]
    )

    session_store.save_cookies(10, "example.com", cookies_json)
    stored_file = tmp_path / "sessions" / "10" / "example.com.json"

    assert stored_file.exists()
    assert "secret-value" not in stored_file.read_text("utf-8")
    assert session_store.list_sessions(10) == ["example.com"]
    assert session_store.load_cookies(10, "example.com")[0]["value"] == "secret-value"
    assert session_store.delete_session(10, "example.com")
    assert session_store.load_cookies(10, "example.com") == []


def test_sessions_are_isolated_per_user(monkeypatch, tmp_path) -> None:
    configure_store(monkeypatch, tmp_path)
    session_store.save_cookies(
        10,
        "example.com",
        '[{"name":"a","value":"user-10","domain":"example.com"}]',
    )
    session_store.save_cookies(
        20,
        "example.com",
        '[{"name":"a","value":"user-20","domain":"example.com"}]',
    )

    assert session_store.load_cookies(10, "example.com")[0]["value"] == "user-10"
    assert session_store.load_cookies(20, "example.com")[0]["value"] == "user-20"


def test_parent_domain_session_matches_subdomain(monkeypatch, tmp_path) -> None:
    configure_store(monkeypatch, tmp_path)
    session_store.save_cookies(
        10,
        "example.com",
        '[{"name":"a","value":"secret","domain":"example.com"}]',
    )

    cookies = session_store.load_cookies_for_domain(10, "www.example.com")
    assert cookies[0]["value"] == "secret"
