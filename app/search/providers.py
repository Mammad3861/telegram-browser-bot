from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import parse_qs, urlparse

import httpx
from bs4 import BeautifulSoup


SEARCH_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "identity",
}
BRAVE_SEARCH_ENDPOINT = "https://api.search.brave.com/res/v1/web/search"


class SearchError(RuntimeError):
    pass


class SearchDisabledError(SearchError):
    pass


class SearchConfigurationError(SearchError):
    pass


class SearchProviderError(SearchError):
    pass


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str | None = None
    source: str | None = None


class SearchProvider(Protocol):
    async def search(self, query: str, limit: int) -> list[SearchResult]: ...

    async def aclose(self) -> None: ...


class DisabledSearchProvider:
    async def search(self, query: str, limit: int) -> list[SearchResult]:
        raise SearchDisabledError("Search provider is disabled")

    async def aclose(self) -> None:
        return None


class HttpSearchProvider:
    def __init__(
        self,
        timeout_seconds: float,
        headers: dict[str, str] | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.client = httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers=headers,
            transport=transport,
        )

    async def aclose(self) -> None:
        await self.client.aclose()


class DuckDuckGoHtmlProvider(HttpSearchProvider):
    def __init__(
        self,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(timeout_seconds, SEARCH_HEADERS, transport)

    async def __aenter__(self) -> "DuckDuckGoHtmlProvider":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def search(self, query: str, limit: int) -> list[SearchResult]:
        try:
            response = await self.client.get(
                "https://html.duckduckgo.com/html/", params={"q": query}
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise SearchProviderError("Search provider timed out") from exc
        except httpx.HTTPError as exc:
            raise SearchProviderError("Search provider request failed") from exc
        encoding = response.encoding or "utf-8"
        try:
            html = response.content.decode(encoding, errors="replace")
        except LookupError:
            html = response.content.decode("utf-8", errors="replace")
        return parse_duckduckgo_html(html, limit)


class BraveSearchApiProvider(HttpSearchProvider):
    def __init__(
        self,
        api_key: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key.strip():
            raise SearchConfigurationError("Brave Search API key is not configured")
        super().__init__(
            timeout_seconds,
            {
                "Accept": "application/json",
                "Accept-Encoding": "identity",
                "X-Subscription-Token": api_key,
            },
            transport,
        )

    async def search(self, query: str, limit: int) -> list[SearchResult]:
        try:
            response = await self.client.get(
                BRAVE_SEARCH_ENDPOINT, params={"q": query, "count": limit}
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as exc:
            raise SearchProviderError("Search provider timed out") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise SearchProviderError("Search provider request failed") from exc
        items = payload.get("web", {}).get("results", []) if isinstance(payload, dict) else []
        return parse_json_results(items, limit, "brave_api", snippet_key="description")


class SearxngSearchProvider(HttpSearchProvider):
    def __init__(
        self,
        base_url: str,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        normalized = base_url.strip().rstrip("/")
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise SearchConfigurationError("SearxNG base URL is not configured")
        self.endpoint = f"{normalized}/search"
        super().__init__(
            timeout_seconds,
            {"Accept": "application/json", "Accept-Encoding": "identity"},
            transport,
        )

    async def search(self, query: str, limit: int) -> list[SearchResult]:
        try:
            response = await self.client.get(
                self.endpoint, params={"q": query, "format": "json"}
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as exc:
            raise SearchProviderError("Search provider timed out") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise SearchProviderError("Search provider request failed") from exc
        items = payload.get("results", []) if isinstance(payload, dict) else []
        return parse_json_results(items, limit, "searxng", snippet_key="content")


def normalize_duckduckgo_url(value: str) -> str:
    if value.startswith("//"):
        value = "https:" + value
    parsed = urlparse(value)
    if parsed.hostname in {"duckduckgo.com", "www.duckduckgo.com"}:
        target = parse_qs(parsed.query).get("uddg")
        if target:
            return target[0]
    return value


def parse_duckduckgo_html(html: str, limit: int) -> list[SearchResult]:
    soup = BeautifulSoup(html, "html.parser")
    results: list[SearchResult] = []
    blocks = soup.select(".result") or soup.select(".web-result")
    for block in blocks:
        link = block.select_one("a.result__a") or block.select_one("h2 a")
        if link is None:
            continue
        title = link.get_text(" ", strip=True)
        href = link.get("href")
        if not title or not isinstance(href, str):
            continue
        snippet_node = block.select_one(".result__snippet") or block.select_one(
            ".result-snippet"
        )
        snippet = snippet_node.get_text(" ", strip=True) if snippet_node else None
        results.append(
            SearchResult(
                title=title,
                url=normalize_duckduckgo_url(href),
                snippet=snippet or None,
                source="duckduckgo_html",
            )
        )
        if len(results) >= limit:
            break
    return results


def parse_json_results(
    items: object, limit: int, source: str, snippet_key: str
) -> list[SearchResult]:
    results: list[SearchResult] = []
    if not isinstance(items, list):
        return results
    for item in items:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        url = item.get("url")
        if not isinstance(title, str) or not title.strip() or not isinstance(url, str):
            continue
        snippet = item.get(snippet_key)
        results.append(
            SearchResult(
                title=title.strip(),
                url=url,
                snippet=snippet.strip() if isinstance(snippet, str) and snippet.strip() else None,
                source=source,
            )
        )
        if len(results) >= limit:
            break
    return results


ProviderFactory = Callable[..., SearchProvider]
SEARCH_PROVIDER_REGISTRY: dict[str, ProviderFactory] = {
    "disabled": lambda **_: DisabledSearchProvider(),
    "duckduckgo_html": lambda **kwargs: DuckDuckGoHtmlProvider(
        kwargs["timeout_seconds"], kwargs.get("transport")
    ),
    "brave_api": lambda **kwargs: BraveSearchApiProvider(
        kwargs.get("brave_api_key", ""),
        kwargs["timeout_seconds"],
        kwargs.get("transport"),
    ),
    "searxng": lambda **kwargs: SearxngSearchProvider(
        kwargs.get("searxng_base_url", ""),
        kwargs["timeout_seconds"],
        kwargs.get("transport"),
    ),
}


def create_search_provider(
    name: str,
    timeout_seconds: float,
    brave_api_key: str = "",
    searxng_base_url: str = "",
    transport: httpx.AsyncBaseTransport | None = None,
) -> SearchProvider:
    factory = SEARCH_PROVIDER_REGISTRY.get(name.strip().lower())
    if factory is None:
        raise SearchConfigurationError("Unsupported search provider")
    return factory(
        timeout_seconds=timeout_seconds,
        brave_api_key=brave_api_key,
        searxng_base_url=searxng_base_url,
        transport=transport,
    )


async def search_web(
    provider_name: str,
    query: str,
    limit: int,
    timeout_seconds: float,
    brave_api_key: str = "",
    searxng_base_url: str = "",
) -> list[SearchResult]:
    provider = create_search_provider(
        provider_name,
        timeout_seconds,
        brave_api_key,
        searxng_base_url,
    )
    try:
        return await provider.search(query, limit)
    finally:
        await provider.aclose()


def provider_display_name(value: str | None) -> str:
    return {
        "duckduckgo_html": "DuckDuckGo",
        "brave_api": "Brave",
        "searxng": "SearxNG",
        "disabled": "Disabled",
    }.get(value or "", value or "Unknown")
