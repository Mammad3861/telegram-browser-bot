import secrets
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from threading import RLock

from app.search.providers import SearchResult


class SearchSessionError(RuntimeError):
    pass


class SearchSessionNotFound(SearchSessionError):
    pass


class SearchSessionNotOwned(SearchSessionError):
    pass


class SearchSessionExpired(SearchSessionError):
    pass


@dataclass(frozen=True)
class SearchSession:
    session_id: str
    user_id: int
    query: str
    results: tuple[SearchResult, ...]
    created_at: datetime
    cancelled: bool = False


class SearchSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, SearchSession] = {}
        self._lock = RLock()

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()

    def create(
        self,
        user_id: int,
        query: str,
        results: list[SearchResult],
        now: datetime | None = None,
    ) -> SearchSession:
        with self._lock:
            session_id = self._new_id()
            session = SearchSession(
                session_id=session_id,
                user_id=user_id,
                query=query,
                results=tuple(results),
                created_at=now or datetime.now(UTC),
            )
            self._sessions[session_id] = session
            return session

    def _new_id(self) -> str:
        while True:
            session_id = secrets.token_hex(4)
            if session_id not in self._sessions:
                return session_id

    def get_for_user(
        self,
        session_id: str,
        user_id: int,
        ttl_minutes: int,
        now: datetime | None = None,
    ) -> SearchSession:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise SearchSessionNotFound("Search session not found")
            if session.user_id != user_id:
                raise SearchSessionNotOwned("Search session belongs to another user")
            if session.cancelled:
                raise SearchSessionNotFound("Search session not found")
            if (now or datetime.now(UTC)) - session.created_at >= timedelta(
                minutes=ttl_minutes
            ):
                self._sessions.pop(session_id, None)
                raise SearchSessionExpired("Search session expired")
            return session

    def update_results(
        self, session_id: str, results: list[SearchResult], now: datetime | None = None
    ) -> SearchSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.cancelled:
                return None
            updated = replace(
                session,
                results=tuple(results),
                created_at=now or datetime.now(UTC),
            )
            self._sessions[session_id] = updated
            return updated

    def cancel(self, session_id: str, user_id: int) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.user_id != user_id or session.cancelled:
                return False
            self._sessions[session_id] = replace(session, cancelled=True)
            return True


search_session_store = SearchSessionStore()
