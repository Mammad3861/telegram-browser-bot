import logging
from pathlib import Path


logger = logging.getLogger(__name__)

GENERATED_FILE_CATEGORIES = {
    "html",
    "html_rendered",
    "files",
    "screenshots",
    "pdf",
}


def _safe_file_details(
    path: Path, downloads_dir: Path
) -> tuple[Path, str, int] | None:
    try:
        if path.is_symlink():
            return None
        root = downloads_dir.resolve(strict=True)
        target = path.resolve(strict=True)
        relative = target.relative_to(root)
        if not relative.parts or relative.parts[0] not in GENERATED_FILE_CATEGORIES:
            return None
        if not target.is_file():
            return None
        return target, relative.parts[0], target.stat().st_size
    except (OSError, RuntimeError, ValueError):
        return None


def is_safe_generated_file(path: Path, downloads_dir: Path) -> bool:
    return _safe_file_details(path, downloads_dir) is not None


def delete_generated_file(path: Path, downloads_dir: Path) -> bool:
    details = _safe_file_details(path, downloads_dir)
    if details is None:
        logger.warning(
            "Refused or unable to delete generated file after Telegram upload: "
            "category=unknown"
        )
        return False

    target, category, size_bytes = details
    try:
        target.unlink()
    except OSError as exc:
        logger.warning(
            "Could not delete generated file after Telegram upload: "
            "category=%s size_bytes=%s exception_type=%s",
            category,
            size_bytes,
            type(exc).__name__,
        )
        return False

    logger.info(
        "Deleted generated file after Telegram upload: category=%s size_bytes=%s",
        category,
        size_bytes,
    )
    return True


def cleanup_sent_file(
    path: Path, downloads_dir: Path, delete_after_send: bool
) -> bool:
    if not delete_after_send:
        return False
    return delete_generated_file(path, downloads_dir)
