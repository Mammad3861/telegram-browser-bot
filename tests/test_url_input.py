from app.core.url_input import normalize_user_url_input


def normalized(value: str) -> str | None:
    result = normalize_user_url_input(value)
    return result.url if result.is_url else None


def test_plain_domain_url_normalization() -> None:
    assert normalized("YouTube.com") == "https://youtube.com"
    assert normalized("youtube.com/watch?v=abc") == "https://youtube.com/watch?v=abc"
    assert normalized("www.youtube.com") == "https://www.youtube.com"
    assert normalized("youtu.be/abc") == "https://youtu.be/abc"
    assert normalized("sub.domain.co/path?x=1#top") == "https://sub.domain.co/path?x=1#top"


def test_url_normalization_rejects_non_urls() -> None:
    assert normalized("hello world") is None
    assert normalized("test") is None
    assert normalized("آموزش پایتون") is None
    assert normalized("hello.com test") is None


def test_url_normalization_rejects_unsupported_schemes() -> None:
    assert normalized("javascript:alert(1)") is None
    assert normalized("file:///tmp/data") is None
    assert normalized("data:text/plain,hello") is None
    assert normalized("ftp://example.com/file") is None
