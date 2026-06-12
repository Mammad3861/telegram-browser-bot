import asyncio
import ipaddress
import socket
from urllib.parse import urlparse

import httpx

from app.config import get_settings
from app.core.url_validation import URLValidationError, validate_url


class FetchError(RuntimeError):
    pass


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36 TelegramBrowserBot/0.9.1"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
    "Connection": "keep-alive",
}

DECODING_ERROR_MESSAGE = (
    "HTTP request failed (DecodingError). Try /html_rendered, /screenshot, "
    "or run on the supported Linux/Docker environment."
)


def safe_response_text(response: httpx.Response) -> str:
    encoding = response.encoding or "utf-8"
    try:
        return response.content.decode(encoding, errors="replace")
    except LookupError:
        return response.content.decode("utf-8", errors="replace")


class HttpFetcher:
    def __init__(
        self,
        transport: httpx.AsyncBaseTransport | None = None,
        max_response_bytes: int | None = None,
    ) -> None:
        settings = get_settings()
        self.max_response_bytes = (
            settings.max_response_bytes
            if max_response_bytes is None
            else max_response_bytes
        )
        self.client = httpx.AsyncClient(
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
            headers=DEFAULT_HEADERS,
            transport=transport,
            event_hooks={"request": [self._validate_request]},
        )

    async def __aenter__(self) -> "HttpFetcher":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.client.aclose()

    async def _validate_destination(self, url: str) -> None:
        validate_url(url)
        hostname = urlparse(url).hostname
        if not hostname:
            raise URLValidationError("URL must include a hostname")

        try:
            addresses = await asyncio.get_running_loop().getaddrinfo(
                hostname, None, type=socket.SOCK_STREAM
            )
        except socket.gaierror as exc:
            raise FetchError("Hostname could not be resolved") from exc

        for address_info in addresses:
            address = ipaddress.ip_address(address_info[4][0])
            if not address.is_global:
                raise URLValidationError(
                    "Hostname resolves to a private or non-public IP address"
                )

    async def _validate_request(self, request: httpx.Request) -> None:
        await self._validate_destination(str(request.url))

    async def fetch(self, url: str) -> httpx.Response:
        validate_url(url)

        try:
            async with self.client.stream("GET", url) as response:
                response.raise_for_status()
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if self.max_response_bytes > 0 and len(content) > self.max_response_bytes:
                        raise FetchError("Response is too large")
                return httpx.Response(
                    status_code=response.status_code,
                    headers=response.headers,
                    content=bytes(content),
                    request=response.request,
                    extensions=response.extensions,
                )
        except httpx.DecodingError as exc:
            raise FetchError(DECODING_ERROR_MESSAGE) from exc
        except httpx.TimeoutException as exc:
            raise FetchError("The request timed out") from exc
        except httpx.ConnectError as exc:
            raise FetchError("Could not connect to the remote site") from exc
        except httpx.HTTPStatusError as exc:
            raise FetchError(
                f"The remote site returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise FetchError(f"HTTP request failed ({type(exc).__name__})") from exc

