import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings
from app.core.access_store import list_allowed_users
from app.core.jobs import ACTIVE_STATUSES, JobStore
from app.version import APP_VERSION


RUNTIME_TARGET = "Linux/Ubuntu 24.04 or Docker"
GENERATED_DIRECTORIES = ("html", "html_rendered", "files", "screenshots", "pdf")


def browser_features_configured() -> bool:
    roots = []
    configured = os.getenv("PLAYWRIGHT_BROWSERS_PATH")
    if configured:
        roots.append(Path(configured))
    roots.extend(
        [
            Path.home() / ".cache" / "ms-playwright",
            Path("/ms-playwright"),
        ]
    )
    return any(
        root.exists() and any(root.glob("chromium-*"))
        for root in roots
    )


def cookie_import_is_enabled(settings: Settings) -> bool:
    return settings.enable_cookie_import and bool(settings.cookie_encryption_key)


def health_payload(settings: Settings) -> dict[str, str | bool]:
    return {
        "status": "ok",
        "version": APP_VERSION,
        "bot_configured": bool(settings.telegram_bot_token),
        "cookie_import_enabled": cookie_import_is_enabled(settings),
        "runtime_target": RUNTIME_TARGET,
        "storage_path_exists": Path(settings.downloads_dir).exists(),
        "browser_features_configured": browser_features_configured(),
    }


@dataclass(frozen=True)
class AdminStatus:
    version: str
    runtime_target: str
    active_jobs: int
    known_jobs: int
    runtime_allowed_users: int
    storage_free_bytes: int
    cookie_import_enabled: bool
    generated_directories: dict[str, bool]


def build_admin_status(settings: Settings, jobs: JobStore) -> AdminStatus:
    all_jobs = jobs.list_jobs()
    downloads_dir = Path(settings.downloads_dir)
    probe_path = downloads_dir if downloads_dir.exists() else downloads_dir.parent
    probe_path = probe_path if probe_path.exists() else Path.cwd()
    return AdminStatus(
        version=APP_VERSION,
        runtime_target=RUNTIME_TARGET,
        active_jobs=sum(job.status in ACTIVE_STATUSES for job in all_jobs),
        known_jobs=len(all_jobs),
        runtime_allowed_users=len(
            list_allowed_users(Path(settings.access_storage_path))
        ),
        storage_free_bytes=shutil.disk_usage(probe_path).free,
        cookie_import_enabled=cookie_import_is_enabled(settings),
        generated_directories={
            name: (downloads_dir / name).exists() for name in GENERATED_DIRECTORIES
        },
    )
