from datetime import UTC, datetime, timedelta

import pytest

from app.search.providers import SearchResult
from app.search.sessions import (
    SearchSessionExpired,
    SearchSessionNotOwned,
    SearchSessionStore,
)


NOW = datetime(2026, 6, 14, 12, 0, tzinfo=UTC)
RESULTS = [SearchResult("Example", "https://example.com")]


def test_search_session_creation() -> None:
    store = SearchSessionStore()
    session = store.create(10, "example", RESULTS, now=NOW)

    assert len(session.session_id) == 8
    assert session.user_id == 10
    assert session.query == "example"
    assert session.results == tuple(RESULTS)
    assert session.cancelled is False


def test_search_session_owner_validation() -> None:
    store = SearchSessionStore()
    session = store.create(10, "example", RESULTS, now=NOW)

    with pytest.raises(SearchSessionNotOwned):
        store.get_for_user(session.session_id, 20, ttl_minutes=30, now=NOW)


def test_search_session_expiration() -> None:
    store = SearchSessionStore()
    session = store.create(10, "example", RESULTS, now=NOW)

    with pytest.raises(SearchSessionExpired):
        store.get_for_user(
            session.session_id,
            10,
            ttl_minutes=30,
            now=NOW + timedelta(minutes=30),
        )

