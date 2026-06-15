from dataclasses import dataclass

import httpx

from app.bot.i18n import text
from app.core.storage import StorageError


@dataclass(frozen=True)
class SafeError:
    key: str
    retryable: bool = False
    status_code: int | None = None


def classify_error(error: BaseException | str) -> SafeError:
    message = str(error).lower()
    if isinstance(error, (TimeoutError, httpx.TimeoutException)) or "timeout" in message:
        return SafeError("error_timeout", retryable=True)
    if isinstance(error, (httpx.ConnectError, httpx.NetworkError)) or any(
        marker in message for marker in ("dns", "connect", "connection")
    ):
        return SafeError("error_connect", retryable=True)
    if isinstance(error, httpx.HTTPStatusError):
        status = error.response.status_code
        return _status_error(status)
    if "403" in message:
        return _status_error(403)
    if "404" in message:
        return _status_error(404)
    if "410" in message:
        return _status_error(410)
    if "429" in message:
        return _status_error(429)
    if "5xx" in message or "500" in message or "502" in message or "503" in message:
        return _status_error(500)
    if "too large" in message or "exceeds" in message:
        return SafeError("error_file_too_large")
    if isinstance(error, StorageError) or "disk" in message or "free space" in message:
        return SafeError("error_disk_low", retryable=True)
    if "provider" in message:
        return SafeError("error_provider_unavailable", retryable=True)
    if "browser" in message or "playwright" in message:
        return SafeError("error_browser_failed", retryable=True)
    if "content_policy" in message or "content policy" in message:
        return SafeError("error_content_policy_blocked")
    if "protected media" in message or "stream" in message:
        return SafeError("error_protected_media_blocked")
    if "proxy" in message or "route" in message:
        return SafeError("error_route_not_configured")
    return SafeError("error_generic")


def _status_error(status: int) -> SafeError:
    if status == 403:
        return SafeError("error_http_403")
    if status == 404:
        return SafeError("error_http_404")
    if status == 410:
        return SafeError("error_http_410")
    if status == 429:
        return SafeError("error_http_429", retryable=True)
    if status >= 500:
        return SafeError("error_http_5xx", retryable=True)
    return SafeError("error_generic", status_code=status)


def user_safe_error_message(error: BaseException | str, language: str) -> str:
    mapped = classify_error(error)
    suffix = text("error_retryable_hint", language) if mapped.retryable else ""
    return text(mapped.key, language) + suffix
