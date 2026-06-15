import httpx

from app.core.error_mapping import classify_error, user_safe_error_message


def test_error_mapper_timeout() -> None:
    mapped = classify_error(httpx.TimeoutException("timeout"))

    assert mapped.key == "error_timeout"
    assert mapped.retryable is True


def test_error_mapper_http_statuses() -> None:
    request = httpx.Request("GET", "https://example.com")
    for status, key in [
        (403, "error_http_403"),
        (410, "error_http_410"),
        (429, "error_http_429"),
        (500, "error_http_5xx"),
    ]:
        error = httpx.HTTPStatusError(
            "failed", request=request, response=httpx.Response(status, request=request)
        )
        assert classify_error(error).key == key


def test_error_mapper_file_too_large_message_is_localized() -> None:
    assert classify_error("File exceeds limit").key == "error_file_too_large"
    assert user_safe_error_message("File exceeds limit", "fa")
