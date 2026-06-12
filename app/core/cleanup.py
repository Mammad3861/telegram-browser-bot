from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path


GENERATED_DIRECTORIES = ("html", "html_rendered", "files", "screenshots", "pdf")


@dataclass(frozen=True)
class CleanupResult:
    deleted_files: int
    freed_bytes: int


def cleanup_generated_files(
    downloads_dir: Path,
    max_age_hours: int,
    now: datetime | None = None,
) -> CleanupResult:
    cutoff = (now or datetime.now(UTC)) - timedelta(hours=max_age_hours)
    deleted_files = 0
    freed_bytes = 0

    for directory_name in GENERATED_DIRECTORIES:
        directory = downloads_dir / directory_name
        if not directory.exists():
            continue
        for path in directory.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            modified_at = datetime.fromtimestamp(path.stat().st_mtime, tz=UTC)
            if modified_at >= cutoff:
                continue
            size = path.stat().st_size
            path.unlink()
            deleted_files += 1
            freed_bytes += size

    return CleanupResult(deleted_files=deleted_files, freed_bytes=freed_bytes)
