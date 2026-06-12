import json

import pytest

from app.core.cookies import (
    CookieValidationError,
    normalize_domain,
    validate_cookies_json,
)


def test_validates_playwright_cookie_json() -> None:
    cookies = validate_cookies_json(
        json.dumps(
            [{"name": "session", "value": "secret", "domain": ".example.com"}]
        ),
        "example.com",
        256,
    )

    assert cookies[0]["domain"] == ".example.com"
    assert cookies[0]["path"] == "/"


def test_rejects_invalid_and_non_list_cookie_json() -> None:
    with pytest.raises(CookieValidationError, match="Invalid cookie JSON"):
        validate_cookies_json("not json", "example.com", 256)
    with pytest.raises(CookieValidationError, match="must be a list"):
        validate_cookies_json('{"name":"cookie"}', "example.com", 256)


def test_rejects_oversized_cookie_json() -> None:
    payload = json.dumps(
        [{"name": "session", "value": "x" * 2048, "domain": "example.com"}]
    )
    with pytest.raises(CookieValidationError, match="exceeds the 1 KB"):
        validate_cookies_json(payload, "example.com", 1)


def test_rejects_unrelated_cookie_domain() -> None:
    payload = json.dumps(
        [{"name": "session", "value": "secret", "domain": "other.com"}]
    )
    with pytest.raises(CookieValidationError, match="does not match"):
        validate_cookies_json(payload, "example.com", 256)


def test_normalizes_domain_and_rejects_internal_domains() -> None:
    assert normalize_domain(".Example.COM.") == "example.com"
    with pytest.raises(CookieValidationError):
        normalize_domain("localhost")
    with pytest.raises(CookieValidationError):
        normalize_domain("192.168.1.1")
