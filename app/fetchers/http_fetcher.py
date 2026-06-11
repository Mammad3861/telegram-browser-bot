import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

from app.config import get_settings
from app.core.url_validation import URLValidationError, validate_url


class FetchError(RuntimeError):
    pass


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36 TelegramBrowserBot/0.1.1"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


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
            follow_redirects=False,
            headers=DEFAULT_HEADERS,
            transport=transport,
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

    async def fetch(self, url: str) -> httpx.Response:
        current_url = validate_url(url)

        try:
            for _ in range(6):
                await self._validate_destination(current_url)
                async with self.client.stream("GET", current_url) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise FetchError("Redirect response has no location")
                        current_url = urljoin(str(response.url), location)
                        continue

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

        raise FetchError("Too many redirects")
