import asyncio

import httpx
import pytest

from app.fetchers.http_fetcher import (
    DECODING_ERROR_MESSAGE,
    DEFAULT_HEADERS,
    FetchError,
    HttpFetcher,
    safe_response_text,
)


async def allow_test_destination(_: str) -> None:
    return None


def run_fetch(handler: httpx.AsyncBaseTransport) -> httpx.Response:
    async def execute() -> httpx.Response:
        async with HttpFetcher(transport=handler) as fetcher:
            fetcher._validate_destination = allow_test_destination  # type: ignore[method-assign]
            return await fetcher.fetch("https://example.com")

    return asyncio.run(execute())


def test_default_headers_are_sent() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["user-agent"] == DEFAULT_HEADERS["User-Agent"]
        assert request.headers["accept"] == DEFAULT_HEADERS["Accept"]
        assert request.headers["accept-language"] == DEFAULT_HEADERS["Accept-Language"]
        assert request.headers["accept-encoding"] == "identity"
        assert request.headers["connection"] == DEFAULT_HEADERS["Connection"]
        return httpx.Response(200, text="ok")

    assert run_fetch(httpx.MockTransport(handler)).text == "ok"


def test_client_follows_redirects() -> None:
    fetcher = HttpFetcher(transport=httpx.MockTransport(lambda _: httpx.Response(200)))
    try:
        assert fetcher.client.follow_redirects is True
    finally:
        asyncio.run(fetcher.client.aclose())


def test_safe_text_decoding_uses_replacement_fallback() -> None:
    response = httpx.Response(
        200,
        headers={"content-type": "text/plain; charset=utf-8"},
        content=b"hello\xffworld",
    )

    assert safe_response_text(response) == "hello\ufffdworld"


def test_safe_text_decoding_falls_back_for_unknown_encoding() -> None:
    response = httpx.Response(200, content="hello".encode())
    response.encoding = "unknown-encoding"

    assert safe_response_text(response) == "hello"


@pytest.mark.parametrize(
    ("exception", "message"),
    [
        (httpx.ReadTimeout("slow response"), "The request timed out"),
        (
            httpx.ConnectError("connection refused"),
            "Could not connect to the remote site",
        ),
        (httpx.ReadError("secret internal detail"), "HTTP request failed (ReadError)"),
    ],
)
def test_http_errors_are_safe_and_useful(
    exception: httpx.HTTPError, message: str
) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        raise exception

    with pytest.raises(FetchError) as error:
        run_fetch(httpx.MockTransport(handler))

    assert str(error.value) == message
    assert "secret internal detail" not in str(error.value)


def test_http_status_error_includes_status_code() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="blocked")

    with pytest.raises(FetchError, match="HTTP 403"):
        run_fetch(httpx.MockTransport(handler))


def test_decoding_error_has_safe_suggestion() -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        raise httpx.DecodingError("unsafe decoder detail")

    with pytest.raises(FetchError) as error:
        run_fetch(httpx.MockTransport(handler))

    assert str(error.value) == DECODING_ERROR_MESSAGE
    assert "unsafe decoder detail" not in str(error.value)
