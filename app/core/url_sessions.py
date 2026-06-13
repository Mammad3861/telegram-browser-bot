import secrets
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from threading import RLock


class URLSessionError(RuntimeError):
    pass


class URLSessionNotFound(URLSessionError):
    pass


class URLSessionNotOwned(URLSessionError):
    pass


class URLSessionExpired(URLSessionError):
    pass


@dataclass(frozen=True)
class URLSession:
    session_id: str
    user_id: int
    url: str
    created_at: datetime
    last_message_id: int | None = None


class URLSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, URLSession] = {}
        self._lock = RLock()

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()

    def create(self, user_id: int, url: str, now: datetime | None = None) -> URLSession:
        with self._lock:
            session_id = self._new_id()
            session = URLSession(
                session_id=session_id,
                user_id=user_id,
                url=url,
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
    ) -> URLSession:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise URLSessionNotFound("URL session not found")
            if session.user_id != user_id:
                raise URLSessionNotOwned("URL session belongs to another user")
            current_time = now or datetime.now(UTC)
            if current_time - session.created_at >= timedelta(minutes=ttl_minutes):
                self._sessions.pop(session_id, None)
                raise URLSessionExpired("URL session expired")
            return session

    def touch(
        self, session_id: str, message_id: int | None = None, now: datetime | None = None
    ) -> URLSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            updated = replace(
                session,
                created_at=now or datetime.now(UTC),
                last_message_id=message_id or session.last_message_id,
            )
            self._sessions[session_id] = updated
            return updated

    def remove(self, session_id: str, user_id: int) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.user_id != user_id:
                return False
            self._sessions.pop(session_id, None)
            return True


url_session_store = URLSessionStore()

