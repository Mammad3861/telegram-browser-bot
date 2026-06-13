from datetime import UTC, datetime, timedelta

import pytest

from app.core.url_sessions import (
    URLSessionExpired,
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

