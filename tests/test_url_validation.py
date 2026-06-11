import pytest

from app.core.url_validation import URLValidationError, validate_url


@pytest.mark.parametrize(
    "url",
    [
        "http://localhost/test",
        "http://127.0.0.1",
        "http://10.0.0.1",
        "http://172.16.0.1",
        "http://192.168.1.1",
        "http://[::1]",
        "file:///etc/passwd",
        "ftp://example.com/file",
        "data://text/plain,hello",
    ],
)
def test_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(URLValidationError):
        validate_url(url)


@pytest.mark.parametrize("url", ["https://example.com", "http://example.com/path"])
def test_accepts_public_http_urls(url: str) -> None:
    assert validate_url(url) == url
