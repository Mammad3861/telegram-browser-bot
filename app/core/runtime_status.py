import os
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings
from app.core.access_store import list_allowed_users
from app.core.config_validation import persistent_directories
from app.core.jobs import ACTIVE_STATUSES, JobStore
from app.core.job_history import load_job_history
from app.core.storage_diagnostics import build_storage_summary
from app.core.url_sessions import URLSessionStore
from app.search.providers import SEARCH_PROVIDER_REGISTRY
from app.search.sessions import SearchSessionStore
from app.version import APP_VERSION


RUNTIME_TARGET = "Linux/Ubuntu 24.04 or Docker"
GENERATED_DIRECTORIES = ("html", "html_rendered", "files", "screenshots", "pdf")
STARTED_AT = datetime.now(UTC)


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


def _directory_writable(path: Path) -> bool:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".write_check"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return True
    except OSError:
        return False


def readiness_payload(settings: Settings) -> dict[str, object]:
    downloads_dir = Path(settings.downloads_dir)
    storage_summary = build_storage_summary(downloads_dir, settings.cleanup_max_age_hours)
    persistent_checks = {
        str(path): _directory_writable(path) for path in persistent_directories(settings)
    }
    checks = {
        "downloads_writable": _directory_writable(downloads_dir),
        "persistent_store_dirs_writable": all(persistent_checks.values()),
        "search_provider_valid": settings.search_provider.lower()
        in SEARCH_PROVIDER_REGISTRY,
        "browser_features_configured": browser_features_configured(),
        "disk_free_above_minimum": storage_summary.free_bytes
        >= settings.min_free_disk_mb * 1024 * 1024,
    }
    return {
        "status": "ok" if all(checks.values()) else "degraded",
        "version": APP_VERSION,
        "runtime_target": RUNTIME_TARGET,
        "checks": checks,
        "persistent_store_dirs": persistent_checks,
        "free_bytes": storage_summary.free_bytes,
        "minimum_free_bytes": settings.min_free_disk_mb * 1024 * 1024,
    }


def liveness_payload() -> dict[str, str]:
    return {"status": "ok", "version": APP_VERSION}


@dataclass(frozen=True)
class AdminStatus:
    version: str
    runtime_target: str
    uptime_seconds: int
    downloads_dir: str
    active_jobs: int
    known_jobs: int
    recent_completed_jobs: int
    runtime_allowed_users: int
    storage_free_bytes: int
    cookie_import_enabled: bool
    generated_directories: dict[str, bool]
    url_sessions: int
    search_sessions: int
    browser_tab_sessions: int
    content_policy_enabled: bool
    search_provider: str
    command_menu_mode: str
    download_mode: str
    cleanup_max_age_hours: int
    cleanup_after_send_enabled: bool
    browser_features_configured: bool


def build_admin_status(settings: Settings, jobs: JobStore) -> AdminStatus:
    all_jobs = jobs.list_jobs()
    downloads_dir = Path(settings.downloads_dir)
    probe_path = downloads_dir if downloads_dir.exists() else downloads_dir.parent
    probe_path = probe_path if probe_path.exists() else Path.cwd()
    return AdminStatus(
        version=APP_VERSION,
        runtime_target=RUNTIME_TARGET,
        uptime_seconds=int((datetime.now(UTC) - STARTED_AT).total_seconds()),
        downloads_dir=str(downloads_dir),
        active_jobs=sum(job.status in ACTIVE_STATUSES for job in all_jobs),
        known_jobs=len(all_jobs),
        recent_completed_jobs=len(load_job_history(Path(settings.job_history_path))),
        runtime_allowed_users=len(
            list_allowed_users(Path(settings.access_storage_path))
        ),
        storage_free_bytes=shutil.disk_usage(probe_path).free,
        cookie_import_enabled=cookie_import_is_enabled(settings),
        generated_directories={
            name: (downloads_dir / name).exists() for name in GENERATED_DIRECTORIES
        },
        url_sessions=URLSessionStore(Path(settings.url_sessions_path)).count(),
        search_sessions=SearchSessionStore(Path(settings.search_sessions_path)).count(),
        browser_tab_sessions=sum(
            1
            for path in Path(settings.browser_tab_state_dir).rglob("*.json")
            if path.is_file()
        )
        if Path(settings.browser_tab_state_dir).exists()
        else 0,
        content_policy_enabled=settings.enable_content_policy,
        search_provider=settings.search_provider,
        command_menu_mode=settings.command_menu_language_mode,
        download_mode=settings.download_mode,
        cleanup_max_age_hours=settings.cleanup_max_age_hours,
        cleanup_after_send_enabled=settings.delete_generated_files_after_send,
        browser_features_configured=browser_features_configured(),
    )
