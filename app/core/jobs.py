import asyncio
import logging
import secrets
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from typing import Literal

from app.config import get_settings
from app.core.job_history import add_job_history_entry, history_entry_from_job


logger = logging.getLogger(__name__)


JobStatus = Literal["pending", "running", "success", "failed", "cancelled"]
ACTIVE_STATUSES = {"pending", "running"}


class JobError(RuntimeError):
    pass


class JobLimitError(JobError):
    pass


@dataclass(frozen=True)
class Job:
    id: str
    user_id: int
    command: str
    url: str
    status: JobStatus
    progress: int
    result_message: str | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None


class JobStore:
    def __init__(
        self, history_path: Path | None = None, history_max_stored: int = 1000
    ) -> None:
        self._jobs: dict[str, Job] = {}
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._lock = RLock()
        self.history_path = history_path
        self.history_max_stored = history_max_stored

    def clear(self) -> None:
        with self._lock:
            for task in self._tasks.values():
                if not task.done():
                    task.cancel()
            self._jobs.clear()
            self._tasks.clear()

    def create_job(
        self,
        user_id: int,
        command: str,
        url: str,
        max_global: int = 3,
        max_per_user: int = 1,
    ) -> Job:
        with self._lock:
            active = [job for job in self._jobs.values() if job.status in ACTIVE_STATUSES]
            if len(active) >= max_global:
                raise JobLimitError("Global job limit reached. Try again later.")
            if sum(job.user_id == user_id for job in active) >= max_per_user:
                raise JobLimitError("You already have the maximum number of active jobs.")

            job_id = self._new_id()
            job = Job(
                id=job_id,
                user_id=user_id,
                command=command,
                url=url,
                status="pending",
                progress=0,
                result_message=None,
                error_message=None,
                created_at=datetime.now(UTC),
            )
            self._jobs[job_id] = job
            return job

    def _new_id(self) -> str:
        while True:
            job_id = secrets.token_hex(4)
            if job_id not in self._jobs:
                return job_id

    def get_job(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update_job(self, job_id: str, **changes: object) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None

            status = changes.get("status")
            if job.status == "cancelled" and status != "cancelled":
                return job
            now = datetime.now(UTC)
            if status == "running" and job.started_at is None:
                changes.setdefault("started_at", now)
            if status in {"success", "failed", "cancelled"}:
                changes.setdefault("finished_at", now)
            if "progress" in changes:
                changes["progress"] = max(0, min(100, int(changes["progress"])))

            updated = replace(job, **changes)
            self._jobs[job_id] = updated
            if (
                self.history_path is not None
                and updated.status in {"success", "failed", "cancelled"}
            ):
                try:
                    add_job_history_entry(
                        self.history_path,
                        history_entry_from_job(updated),
                        self.history_max_stored,
                    )
                except OSError as exc:
                    logger.warning(
                        "Could not persist completed job history: job_id=%s "
                        "exception_type=%s",
                        updated.id,
                        type(exc).__name__,
                    )
            return updated

    def list_user_jobs(self, user_id: int) -> list[Job]:
        with self._lock:
            jobs = [job for job in self._jobs.values() if job.user_id == user_id]
            return sorted(jobs, key=lambda job: job.created_at, reverse=True)

    def list_jobs(self) -> list[Job]:
        with self._lock:
            return sorted(
                self._jobs.values(), key=lambda job: job.created_at, reverse=True
            )

    def register_task(self, job_id: str, task: asyncio.Task[None]) -> None:
        with self._lock:
            self._tasks[job_id] = task
        task.add_done_callback(lambda _: self._remove_task(job_id))

    def _remove_task(self, job_id: str) -> None:
        with self._lock:
            self._tasks.pop(job_id, None)

    def cancel_job(self, job_id: str, user_id: int, is_admin: bool = False) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or (job.user_id != user_id and not is_admin):
                return False
            if job.status not in ACTIVE_STATUSES:
                return False
            self.update_job(job_id, status="cancelled", progress=job.progress)
            task = self._tasks.get(job_id)
            if task and not task.done():
                task.cancel()
            return True


_settings = get_settings()
job_store = JobStore(
    Path(_settings.job_history_path), _settings.job_history_max_stored
)


def create_job(*args, **kwargs) -> Job:
    return job_store.create_job(*args, **kwargs)


def get_job(job_id: str) -> Job | None:
    return job_store.get_job(job_id)


def update_job(job_id: str, **changes: object) -> Job | None:
    return job_store.update_job(job_id, **changes)


def list_user_jobs(user_id: int) -> list[Job]:
    return job_store.list_user_jobs(user_id)


def cancel_job(job_id: str, user_id: int, is_admin: bool = False) -> bool:
    return job_store.cancel_job(job_id, user_id, is_admin)
