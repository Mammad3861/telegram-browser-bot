import re
from datetime import UTC, datetime
from email.message import Message
from pathlib import Path
from urllib.parse import unquote, urlparse


SUPPORTED_EXTENSIONS = {
    "pdf", "zip", "rar", "7z", "tar", "gz", "mp4", "mkv", "mp3", "wav",
    "jpg", "jpeg", "png", "webp", "doc", "docx", "xls", "xlsx", "ppt",
    "pptx", "csv", "json", "xml", "txt", "msi", "exe", "dmg", "pkg",
    "deb", "rpm", "tgz",
}

DOWNLOADABLE_CONTENT_TYPES = {
    "application/7z-compressed",
    "application/gzip",
    "application/zip",
    "application/x-gzip",
    "application/x-rpm",
    "application/json",
    "application/msword",
    "application/pdf",
    "application/rar",
    "application/vnd.ms-excel",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/x-7z-compressed",
    "application/x-rar-compressed",
    "application/x-tar",
    "application/xml",
    "application/octet-stream",
    "application/x-msdownload",
    "application/x-apple-diskimage",
    "application/vnd.debian.binary-package",
    "audio/mpeg",
    "audio/wav",
    "image/jpeg",
    "image/png",
    "image/webp",
    "text/csv",
    "text/plain",
    "text/xml",
    "video/mp4",
    "video/x-matroska",
}

WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


def content_disposition_filename(value: str | None) -> str | None:
    if not value:
        return None
    message = Message()
    message["content-disposition"] = value
    filename = message.get_filename()
    return unquote(filename).strip() if filename else None


def url_extension(url: str) -> str:
    return Path(unquote(urlparse(url).path)).suffix.lower().lstrip(".")


def is_direct_file(
    url: str,
    content_type: str | None = None,
    content_disposition: str | None = None,
) -> bool:
    disposition_filename = content_disposition_filename(content_disposition)
    if disposition_filename:
        extension = Path(disposition_filename).suffix.lower().lstrip(".")
        if extension:
            return extension in SUPPORTED_EXTENSIONS

    extension = url_extension(url)
    if extension in SUPPORTED_EXTENSIONS:
        return True

    if content_disposition and "attachment" in content_disposition.lower():
        return True
    media_type = (content_type or "").split(";", 1)[0].strip().lower()
    if media_type in {"text/html", "application/xhtml+xml"}:
        return False
    return media_type in DOWNLOADABLE_CONTENT_TYPES


def sanitize_filename(filename: str, max_length: int = 180) -> str:
    filename = filename.replace("/", "_").replace("\\", "_")
    filename = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", filename)
    filename = re.sub(r"\s+", " ", filename).strip(" .")
    if not filename:
        return "downloaded_file"

    path = Path(filename)
    stem = path.stem
    suffix = path.suffix
    if stem.upper() in WINDOWS_RESERVED_NAMES:
        stem = f"_{stem}"
    available = max(1, max_length - len(suffix))
    return f"{stem[:available]}{suffix}".rstrip(" .")


def choose_filename(
    url: str,
    content_disposition: str | None,
    timestamp: datetime | None = None,
) -> str:
    filename = content_disposition_filename(content_disposition)
    if not filename:
        filename = Path(unquote(urlparse(url).path)).name
    if not filename:
        created_at = timestamp or datetime.now(UTC)
        filename = f"downloaded_file_{created_at.strftime('%Y%m%d_%H%M%S')}"
    return sanitize_filename(filename)
