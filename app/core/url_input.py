from dataclasses import dataclass
from urllib.parse import urlsplit, urlunsplit


UNSUPPORTED_SCHEMES = {"javascript", "file", "data", "ftp"}


@dataclass(frozen=True)
class NormalizedUrlResult:
    is_url: bool
    url: str | None = None
    error: str | None = None


def normalize_user_url_input(text: str | None) -> NormalizedUrlResult:
    if text is None:
        return NormalizedUrlResult(False, error="empty")
    value = text.strip()
    if not value:
        return NormalizedUrlResult(False, error="empty")
    if any(character.isspace() or not character.isprintable() for character in value):
        return NormalizedUrlResult(False, error="ambiguous")

    candidate = value
    scheme_separator = candidate.find(":")
    if scheme_separator >= 0:
        scheme = candidate[:scheme_separator].lower()
        if scheme in UNSUPPORTED_SCHEMES:
            return NormalizedUrlResult(False, error="unsupported_scheme")
        if scheme not in {"http", "https"}:
            return NormalizedUrlResult(False, error="unsupported_scheme")
    else:
        candidate = "https://" + candidate

    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return NormalizedUrlResult(False, error="invalid")

    try:
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        return NormalizedUrlResult(False, error="invalid_domain")
    if not hostname or "." not in hostname:
        return NormalizedUrlResult(False, error="invalid_domain")

    netloc = parsed.netloc
    if "@" in netloc:
        return NormalizedUrlResult(False, error="invalid_domain")
    lower_host = hostname.lower()
    if port is not None:
        lower_host = f"{lower_host}:{port}"
    normalized = urlunsplit(
        (
            parsed.scheme.lower(),
            lower_host,
            parsed.path,
            parsed.query,
            parsed.fragment,
        )
    )
    return NormalizedUrlResult(True, normalized)
