import json
import logging
import secrets
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock

from app.config import get_settings


logger = logging.getLogger(__name__)


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
    cancelled: bool = False
    last_message_id: int | None = None
    title: str | None = None
    history: tuple[str, ...] = ()
    updated_at: datetime | None = None

    @property
    def current_url(self) -> str:
        return self.url


class URLSessionStore:
    def __init__(self, path: Path | None = None, max_stored: int = 500) -> None:
        self._sessions: dict[str, URLSession] = {}
        self._lock = RLock()
        self.path = path
        self.max_stored = max_stored
        self._load()

    def _load(self) -> None:
        if self.path is None or not self.path.exists():
            return
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Could not load URL sessions; using empty store: exception_type=%s",
                type(exc).__name__,
            )
            return
        raw_sessions = payload.get("sessions", []) if isinstance(payload, dict) else []
        for item in raw_sessions:
            if not isinstance(item, dict):
                continue
            try:
                session = URLSession(
                    session_id=str(item["session_id"]),
                    user_id=int(item["user_id"]),
                    url=str(item["url"]),
                    created_at=datetime.fromisoformat(str(item["created_at"])),
                    cancelled=bool(item.get("cancelled", False)),
                    last_message_id=(
                        int(item["last_message_id"])
                        if item.get("last_message_id") is not None
                        else None
                    ),
                    title=str(item["title"]) if item.get("title") else None,
                    history=tuple(str(value) for value in item.get("history", [])),
                    updated_at=(
                        datetime.fromisoformat(str(item["updated_at"]))
                        if item.get("updated_at")
                        else None
                    ),
                )
            except (KeyError, TypeError, ValueError):
                continue
            self._sessions[session.session_id] = session

    def _save(self) -> None:
        if self.path is None:
            return
        sessions = sorted(
            self._sessions.values(), key=lambda item: item.created_at, reverse=True
        )[: self.max_stored]
        self._sessions = {item.session_id: item for item in sessions}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        payload = {
            "sessions": [
                {
                    **asdict(item),
                    "created_at": item.created_at.isoformat(),
                    "updated_at": item.updated_at.isoformat() if item.updated_at else None,
                    "history": list(item.history),
                }
                for item in sessions
            ]
        }
        temporary.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        temporary.replace(self.path)

    def clear(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._save()

    def count(self) -> int:
        with self._lock:
            return len(self._sessions)

    def create(self, user_id: int, url: str, now: datetime | None = None) -> URLSession:
        with self._lock:
            session_id = self._new_id()
            session = URLSession(
                session_id=session_id,
                user_id=user_id,
                url=url,
                created_at=now or datetime.now(UTC),
                updated_at=now or datetime.now(UTC),
            )
            self._sessions[session_id] = session
            self._save()
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
            if session.cancelled:
                raise URLSessionNotFound("URL session was cancelled")
            current_time = now or datetime.now(UTC)
            if current_time - session.created_at >= timedelta(minutes=ttl_minutes):
                self._sessions.pop(session_id, None)
                self._save()
                raise URLSessionExpired("URL session expired")
            return session

    def touch(
        self, session_id: str, message_id: int | None = None, now: datetime | None = None
    ) -> URLSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.cancelled:
                return None
            updated = replace(
                session,
                created_at=now or datetime.now(UTC),
                last_message_id=message_id or session.last_message_id,
                updated_at=now or datetime.now(UTC),
            )
            self._sessions[session_id] = updated
            self._save()
            return updated

    def cancel(self, session_id: str, user_id: int) -> bool:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.user_id != user_id or session.cancelled:
                return False
            self._sessions[session_id] = replace(session, cancelled=True)
            self._save()
            return True

    def remove(self, session_id: str, user_id: int) -> bool:
        return self.cancel(session_id, user_id)

    def navigate(
        self,
        session_id: str,
        user_id: int,
        url: str,
        title: str | None = None,
        now: datetime | None = None,
    ) -> URLSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.user_id != user_id or session.cancelled:
                return None
            updated = replace(
                session,
                url=url,
                title=title,
                history=(*session.history, session.url),
                updated_at=now or datetime.now(UTC),
            )
            self._sessions[session_id] = updated
            self._save()
            return updated

    def back(self, session_id: str, user_id: int, now: datetime | None = None) -> URLSession | None:
        with self._lock:
            session = self._sessions.get(session_id)
            if (
                session is None
                or session.user_id != user_id
                or session.cancelled
                or not session.history
            ):
                return None
            updated = replace(
                session,
                url=session.history[-1],
                history=session.history[:-1],
                title=None,
                updated_at=now or datetime.now(UTC),
            )
            self._sessions[session_id] = updated
            self._save()
            return updated


_settings = get_settings()
url_session_store = URLSessionStore(
    Path(_settings.url_sessions_path), _settings.url_session_max_stored
)
