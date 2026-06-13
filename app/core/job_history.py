import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from threading import RLock
from urllib.parse import urlparse


logger = logging.getLogger(__name__)
_history_lock = RLock()


@dataclass(frozen=True)
class JobHistoryEntry:
    job_id: str
    user_id: int
    command: str
    url_domain: str
    status: str
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    error_message: str | None = None
    result_type: str | None = None


def load_job_history(path: Path) -> list[JobHistoryEntry]:
    with _history_lock:
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Could not load job history; using empty history: exception_type=%s",
                type(exc).__name__,
            )
            return []
    raw_jobs = payload.get("jobs", []) if isinstance(payload, dict) else []
    entries: list[JobHistoryEntry] = []
    for item in raw_jobs:
        if not isinstance(item, dict):
            continue
        try:
            entries.append(
                JobHistoryEntry(
                    job_id=str(item["job_id"]),
                    user_id=int(item["user_id"]),
                    command=str(item["command"]),
                    url_domain=str(item.get("url_domain", "")),
                    status=str(item["status"]),
                    created_at=datetime.fromisoformat(str(item["created_at"])),
                    started_at=(
                        datetime.fromisoformat(str(item["started_at"]))
                        if item.get("started_at")
                        else None
                    ),
                    finished_at=(
                        datetime.fromisoformat(str(item["finished_at"]))
                        if item.get("finished_at")
                        else None
                    ),
                    error_message=(
                        str(item["error_message"])
                        if item.get("error_message") is not None
                        else None
                    ),
                    result_type=(
                        str(item["result_type"])
                        if item.get("result_type") is not None
                        else None
                    ),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(entries, key=lambda item: item.created_at, reverse=True)


def save_job_history(
    path: Path, entries: list[JobHistoryEntry], max_stored: int
) -> None:
    with _history_lock:
        limited = sorted(entries, key=lambda item: item.created_at, reverse=True)[
            :max_stored
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        payload = {
            "jobs": [
                {
                    **asdict(item),
                    "created_at": item.created_at.isoformat(),
                    "started_at": (
                        item.started_at.isoformat() if item.started_at else None
                    ),
                    "finished_at": (
                        item.finished_at.isoformat() if item.finished_at else None
                    ),
                }
                for item in limited
            ]
        }
        temporary.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        temporary.replace(path)


def add_job_history_entry(
    path: Path, entry: JobHistoryEntry, max_stored: int
) -> None:
    with _history_lock:
        entries = [item for item in load_job_history(path) if item.job_id != entry.job_id]
        entries.append(entry)
        save_job_history(path, entries, max_stored)


def find_job_history(path: Path, job_id: str) -> JobHistoryEntry | None:
    return next(
        (item for item in load_job_history(path) if item.job_id == job_id), None
    )


def list_user_job_history(path: Path, user_id: int) -> list[JobHistoryEntry]:
    return [item for item in load_job_history(path) if item.user_id == user_id]


def purge_job_history(path: Path) -> int:
    entries = load_job_history(path)
    if path.exists():
        save_job_history(path, [], 0)
    return len(entries)


def history_entry_from_job(job: object) -> JobHistoryEntry:
    url = str(getattr(job, "url", ""))
    domain = urlparse(url).hostname or ""
    error = getattr(job, "error_message", None)
    safe_error = str(error)[:500] if error else None
    command = str(getattr(job, "command"))
    return JobHistoryEntry(
        job_id=str(getattr(job, "id")),
        user_id=int(getattr(job, "user_id")),
        command=command,
        url_domain=domain,
        status=str(getattr(job, "status")),
        created_at=getattr(job, "created_at"),
        started_at=getattr(job, "started_at"),
        finished_at=getattr(job, "finished_at"),
        error_message=safe_error,
        result_type=command,
    )

