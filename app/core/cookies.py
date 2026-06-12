import ipaddress
import json
import re
from typing import Any

from app.config import get_settings


class CookieValidationError(ValueError):
    pass


DOMAIN_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def normalize_domain(domain: str) -> str:
    value = domain.strip().lower().rstrip(".")
    if value.startswith("."):
        value = value[1:]
    if not value or "://" in value or "/" in value or "@" in value or ":" in value:
        raise CookieValidationError("Invalid domain")
    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise CookieValidationError("Invalid domain") from exc
    if value == "localhost" or value.endswith(".localhost"):
        raise CookieValidationError("Local or internal domains are not allowed")
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        address = None
    if address is not None:
        if not address.is_global:
            raise CookieValidationError("Local or private IP domains are not allowed")
        return value
    labels = value.split(".")
    if len(labels) < 2 or any(not DOMAIN_LABEL.fullmatch(label) for label in labels):
        raise CookieValidationError("Invalid domain")
    return value


def domain_matches(hostname: str, session_domain: str) -> bool:
    host = normalize_domain(hostname)
    domain = normalize_domain(session_domain)
    return host == domain or host.endswith(f".{domain}")


def validate_cookies_json(
    cookies_json: str,
    expected_domain: str | None = None,
    max_size_kb: int | None = None,
) -> list[dict[str, Any]]:
    limit_kb = max_size_kb or get_settings().max_cookie_import_size_kb
    if len(cookies_json.encode("utf-8")) > limit_kb * 1024:
        raise CookieValidationError(f"Cookie payload exceeds the {limit_kb} KB limit")
    try:
        payload = json.loads(cookies_json)
    except json.JSONDecodeError as exc:
        raise CookieValidationError("Invalid cookie JSON") from exc
    if not isinstance(payload, list):
        raise CookieValidationError("Cookie JSON must be a list")

    target = normalize_domain(expected_domain) if expected_domain else None
    normalized: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise CookieValidationError("Each cookie must be a JSON object")
        if not all(key in item for key in ("name", "value", "domain")):
            raise CookieValidationError("Each cookie requires name, value, and domain")
        if not isinstance(item["name"], str) or not isinstance(item["value"], str):
            raise CookieValidationError("Cookie name and value must be strings")
        if not isinstance(item["domain"], str):
            raise CookieValidationError("Cookie domain must be a string")
        cookie_domain = normalize_domain(item["domain"])
        if target and not domain_matches(target, cookie_domain):
            raise CookieValidationError("Cookie domain does not match the requested domain")
        cookie = dict(item)
        cookie["domain"] = (
            f".{cookie_domain}" if item["domain"].strip().startswith(".") else cookie_domain
        )
        cookie.setdefault("path", "/")
        normalized.append(cookie)
    return normalized
