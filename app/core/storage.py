import shutil
from pathlib import Path


class StorageError(RuntimeError):
    pass


def has_minimum_free_space(directory: Path, minimum_free_mb: int) -> bool:
    directory.mkdir(parents=True, exist_ok=True)
    free_bytes = shutil.disk_usage(directory).free
    return free_bytes >= minimum_free_mb * 1024 * 1024


def ensure_free_space(directory: Path, minimum_free_mb: int) -> None:
    if not has_minimum_free_space(directory, minimum_free_mb):
        raise StorageError("Not enough free disk space to save this HTML file")
