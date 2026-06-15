import shutil
from dataclasses import dataclass
from pathlib import Path


STORAGE_CATEGORIES = (
    "files",
    "screenshots",
    "pdf",
    "html",
    "html_rendered",
    "sessions",
    "policies",
    "jobs",
    "ui_sessions",
)


@dataclass(frozen=True)
class StorageSummary:
    downloads_dir: Path
    free_bytes: int
    categories: dict[str, int]
    cleanup_max_age_hours: int


def directory_size(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for item in path.rglob("*"):
        if item.is_file() and not item.is_symlink():
            total += item.stat().st_size
    return total


def build_storage_summary(downloads_dir: Path, cleanup_max_age_hours: int) -> StorageSummary:
    probe = downloads_dir if downloads_dir.exists() else downloads_dir.parent
    probe = probe if probe.exists() else Path.cwd()
    return StorageSummary(
        downloads_dir=downloads_dir,
        free_bytes=shutil.disk_usage(probe).free,
        categories={
            category: directory_size(downloads_dir / category)
            for category in STORAGE_CATEGORIES
        },
        cleanup_max_age_hours=cleanup_max_age_hours,
    )
