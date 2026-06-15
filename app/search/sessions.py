import json
import logging
import secrets
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import RLock

from app.config import get_settings
from app.search.providers import SearchResult


logger = logging.getLogger(__name__)


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
    def __init__(self, path: Path | None = None, max_stored: int = 300) -> None:
        self._sessions: dict[str, SearchSession] = {}
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
                "Could not load search sessions; using empty store: exception_type=%s",
                type(exc).__name__,
            )
            return
        raw_sessions = payload.get("sessions", []) if isinstance(payload, dict) else []
        for item in raw_sessions:
            if not isinstance(item, dict):
                continue
            try:
                results = tuple(
                    SearchResult(
                        title=str(result["title"]),
                        url=str(result["url"]),
                        snippet=(
                            str(result["snippet"])
                            if result.get("snippet") is not None
                            else None
                        ),
                        source=(
                            str(result["source"])
                            if result.get("source") is not None
                            else None
                        ),
                    )
                    for result in item.get("results", [])
                    if isinstance(result, dict)
                )
                session = SearchSession(
                    session_id=str(item["session_id"]),
                    user_id=int(item["user_id"]),
                    query=str(item["query"]),
                    results=results,
                    created_at=datetime.fromisoformat(str(item["created_at"])),
                    cancelled=bool(item.get("cancelled", False)),
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
                    "session_id": item.session_id,
                    "user_id": item.user_id,
                    "query": item.query,
                    "results": [asdict(result) for result in item.results],
                    "created_at": item.created_at.isoformat(),
                    "cancelled": item.cancelled,
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
                self._save()
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


_settings = get_settings()
search_session_store = SearchSessionStore(
    Path(_settings.search_sessions_path), _settings.search_session_max_stored
)
