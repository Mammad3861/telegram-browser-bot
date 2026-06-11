import ipaddress
from urllib.parse import urlparse


class URLValidationError(ValueError):
    pass


def is_blocked_ip(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return not address.is_global


def validate_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        port = parsed.port
    except ValueError as exc:
        raise URLValidationError("Invalid URL") from exc

    if parsed.scheme not in {"http", "https"}:
        raise URLValidationError("Only http and https URLs are allowed")
    if not parsed.hostname:
        raise URLValidationError("URL must include a hostname")
    if parsed.username or parsed.password:
        raise URLValidationError("Credentials in URLs are not allowed")
    if port is not None and not 1 <= port <= 65535:
        raise URLValidationError("Invalid port")

    hostname = parsed.hostname.rstrip(".").lower()
    if hostname == "localhost" or hostname.endswith(".localhost"):
        raise URLValidationError("Localhost is not allowed")
    if is_blocked_ip(hostname):
        raise URLValidationError("Private or non-public IP addresses are not allowed")

    return url
