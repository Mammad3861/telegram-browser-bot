import re
from dataclasses import dataclass
from datetime import UTC, datetime
from email.message import Message
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


SUPPORTED_EXTENSIONS = {
    "zip", "7z", "rar", "tar", "gz", "tgz", "bz2", "xz",
    "msi", "exe", "dmg", "pkg", "deb", "rpm", "appimage",
    "pdf", "epub", "mobi",
    "png", "jpg", "jpeg", "webp", "gif", "svg",
    "txt", "csv", "json", "xml", "yaml", "yml", "log",
    "mp3", "wav", "ogg", "flac", "mp4", "webm", "mkv",
    "doc", "docx", "xls", "xlsx", "ppt", "pptx",
}
STREAM_MANIFEST_EXTENSIONS = {"m3u8", "mpd"}
DOWNLOAD_QUERY_KEYS = {"download", "file", "filename", "attachment", "export"}

DOWNLOADABLE_CONTENT_TYPES = {
    "application/7z-compressed", "application/gzip", "application/zip",
    "application/x-gzip", "application/x-rpm", "application/json",
    "application/msword", "application/pdf", "application/rar",
    "application/epub+zip", "application/x-mobipocket-ebook",
    "application/vnd.ms-excel", "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/x-7z-compressed", "application/x-rar-compressed",
    "application/x-tar", "application/xml", "application/octet-stream",
    "application/x-msdownload", "application/x-apple-diskimage",
    "application/vnd.debian.binary-package", "application/x-bzip2",
    "application/x-xz", "audio/mpeg", "audio/wav", "audio/ogg",
    "audio/flac", "image/jpeg", "image/png", "image/webp", "image/gif",
    "image/svg+xml", "text/csv", "text/plain", "text/xml",
    "application/yaml", "text/yaml", "video/mp4", "video/webm",
    "video/x-matroska",
}

WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{number}" for number in range(1, 10)),
    *(f"LPT{number}" for number in range(1, 10)),
}


@dataclass(frozen=True)
class FileDetection:
    confidence: str
    reason: str
    content_type: str | None = None
    content_length: int | None = None
    final_url: str | None = None
    filename: str | None = None

    @property
    def confident(self) -> bool:
        return self.confidence == "confident"


def content_disposition_filename(value: str | None) -> str | None:
    if not value:
        return None
    message = Message()
    message["content-disposition"] = value
    filename = message.get_filename()
    return unquote(filename).strip() if filename else None


def url_extension(url: str) -> str:
    return Path(unquote(urlparse(url).path)).suffix.lower().lstrip(".")


def has_download_query_hint(url: str) -> bool:
    query = parse_qs(urlparse(url).query, keep_blank_values=True)
    return any(key.lower() in DOWNLOAD_QUERY_KEYS for key in query)


def detect_file(
    url: str,
    content_type: str | None = None,
    content_disposition: str | None = None,
    content_length: int | None = None,
) -> FileDetection:
    filename = content_disposition_filename(content_disposition)
    media_type = (content_type or "").split(";", 1)[0].strip().lower() or None
    extension = (
        Path(filename).suffix.lower().lstrip(".") if filename else url_extension(url)
    )
    if extension in STREAM_MANIFEST_EXTENSIONS:
        return FileDetection("rejected", "stream_manifest", media_type, content_length, url, filename)
    if content_disposition and "attachment" in content_disposition.lower():
        return FileDetection("confident", "content_disposition", media_type, content_length, url, filename)
    if media_type in {"text/html", "application/xhtml+xml"}:
        if extension in SUPPORTED_EXTENSIONS:
            return FileDetection("verify", "file_extension", media_type, content_length, url, filename)
        return FileDetection("rejected", "html_content", media_type, content_length, url, filename)
    if extension in SUPPORTED_EXTENSIONS:
        return FileDetection("confident", "file_extension", media_type, content_length, url, filename)
    if media_type in DOWNLOADABLE_CONTENT_TYPES:
        return FileDetection("confident", "content_type", media_type, content_length, url, filename)
    if has_download_query_hint(url) or filename:
        return FileDetection("uncertain", "download_hint", media_type, content_length, url, filename)
    return FileDetection("uncertain", "unknown_response", media_type, content_length, url, filename)


def is_direct_file(
    url: str,
    content_type: str | None = None,
    content_disposition: str | None = None,
) -> bool:
    return detect_file(url, content_type, content_disposition).confident


def looks_like_download_link(url: str, text: str = "", rel: str = "") -> bool:
    extension = url_extension(url)
    if extension in STREAM_MANIFEST_EXTENSIONS:
        return False
    if extension in SUPPORTED_EXTENSIONS:
        return True
    hints = f"{text} {rel}".lower()
    return has_download_query_hint(url) or any(
        word in hints for word in ("download", "attachment", "file", "دریافت", "دانلود")
    )


def looks_like_html(data: bytes) -> bool:
    sample = data[:1024].lstrip().lower()
    return sample.startswith((b"<!doctype html", b"<html", b"<head", b"<body"))


def sanitize_filename(filename: str, max_length: int = 180) -> str:
    filename = filename.replace("/", "_").replace("\\", "_")
    filename = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "_", filename)
    filename = re.sub(r"\s+", " ", filename).strip(" .")
    if not filename:
        return "downloaded_file"
    path = Path(filename)
    stem, suffix = path.stem, path.suffix
    if stem.upper() in WINDOWS_RESERVED_NAMES:
        stem = f"_{stem}"
    return f"{stem[:max(1, max_length - len(suffix))]}{suffix}".rstrip(" .")


def choose_filename(
    url: str, content_disposition: str | None, timestamp: datetime | None = None
) -> str:
    filename = content_disposition_filename(content_disposition)
    if not filename:
        filename = Path(unquote(urlparse(url).path)).name
    if not filename:
        created_at = timestamp or datetime.now(UTC)
        filename = f"downloaded_file_{created_at.strftime('%Y%m%d_%H%M%S')}"
    return sanitize_filename(filename)
