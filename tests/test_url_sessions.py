from datetime import UTC, datetime, timedelta

import pytest

from app.core.url_sessions import (
    URLSessionExpired,
    URLSessionNotFound,
    URLSessionNotOwned,
    URLSessionStore,
)


NOW = datetime(2026, 6, 13, 12, 0, tzinfo=UTC)


def test_url_session_creation() -> None:
    store = URLSessionStore()
    session = store.create(123, "https://example.com", now=NOW)

    assert len(session.session_id) == 8
    assert session.user_id == 123
    assert session.url == "https://example.com"
    assert session.created_at == NOW
    assert session.cancelled is False


def test_url_session_owner_validation() -> None:
    store = URLSessionStore()
    session = store.create(123, "https://example.com", now=NOW)

    with pytest.raises(URLSessionNotOwned):
        store.get_for_user(session.session_id, 456, ttl_minutes=60, now=NOW)


def test_url_session_expiration() -> None:
    store = URLSessionStore()
    session = store.create(123, "https://example.com", now=NOW)

    with pytest.raises(URLSessionExpired):
        store.get_for_user(
            session.session_id,
            123,
            ttl_minutes=60,
            now=NOW + timedelta(minutes=60),
        )


def test_refresh_extends_url_session_lifetime() -> None:
    store = URLSessionStore()
    session = store.create(123, "https://example.com", now=NOW)
    refreshed = store.touch(
        session.session_id, message_id=99, now=NOW + timedelta(minutes=30)
    )

    assert refreshed is not None
    assert refreshed.last_message_id == 99
    assert store.get_for_user(
        session.session_id,
        123,
        ttl_minutes=60,
        now=NOW + timedelta(minutes=75),
    ) == refreshed


def test_cancelling_url_session_makes_it_unusable() -> None:
    store = URLSessionStore()
    session = store.create(123, "https://example.com", now=NOW)

    assert store.cancel(session.session_id, 123)
    with pytest.raises(URLSessionNotFound):
        store.get_for_user(session.session_id, 123, ttl_minutes=60, now=NOW)
    assert not store.cancel(session.session_id, 123)


def test_user_cannot_cancel_another_users_session() -> None:
    store = URLSessionStore()
    session = store.create(123, "https://example.com", now=NOW)

    assert not store.cancel(session.session_id, 456)
    assert store.get_for_user(session.session_id, 123, ttl_minutes=60, now=NOW) == session


def test_url_session_persists_across_store_reload(tmp_path) -> None:
    path = tmp_path / "ui_sessions" / "url_sessions.json"
    session = URLSessionStore(path).create(123, "https://example.com", now=NOW)

    loaded = URLSessionStore(path).get_for_user(
        session.session_id, 123, ttl_minutes=60, now=NOW
    )

    assert loaded == session


def test_loaded_expired_url_session_is_rejected(tmp_path) -> None:
    path = tmp_path / "url_sessions.json"
    session = URLSessionStore(path).create(123, "https://example.com", now=NOW)

    with pytest.raises(URLSessionExpired):
        URLSessionStore(path).get_for_user(
            session.session_id,
            123,
            ttl_minutes=60,
            now=NOW + timedelta(minutes=60),
        )


def test_corrupted_url_session_json_falls_back_to_empty_store(tmp_path) -> None:
    path = tmp_path / "url_sessions.json"
    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(URLSessionNotFound):
        URLSessionStore(path).get_for_user("missing", 123, ttl_minutes=60, now=NOW)


def test_tab_navigation_and_back_history() -> None:
    store = URLSessionStore()
    session = store.create(123, "https://example.com", now=NOW)

    navigated = store.navigate(
        session.session_id, 123, "https://example.com/next", "Next", now=NOW
    )
    assert navigated is not None
    assert navigated.current_url == "https://example.com/next"
    assert navigated.history == ("https://example.com",)

    previous = store.back(session.session_id, 123, now=NOW)
    assert previous is not None
    assert previous.current_url == "https://example.com"
    assert previous.history == ()


def test_tab_navigation_persists_updated_url_and_title(tmp_path) -> None:
    path = tmp_path / "url_sessions.json"
    store = URLSessionStore(path)
    session = store.create(123, "https://example.com", now=NOW)

    store.navigate(session.session_id, 123, "https://example.com/home", "Home", now=NOW)
    loaded = URLSessionStore(path).get_for_user(session.session_id, 123, 60, now=NOW)

    assert loaded.current_url == "https://example.com/home"
    assert loaded.title == "Home"
