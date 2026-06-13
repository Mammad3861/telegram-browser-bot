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


class SearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str | None = None
    source: str | None = None


class SearchProvider(Protocol):
    async def search(self, query: str, limit: int) -> list[SearchResult]: ...


class DisabledSearchProvider:
    async def search(self, query: str, limit: int) -> list[SearchResult]:
        raise SearchError("Search provider is disabled")


class DuckDuckGoHtmlProvider:
    def __init__(
        self,
        timeout_seconds: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.client = httpx.AsyncClient(
            timeout=timeout_seconds,
            follow_redirects=True,
            headers=SEARCH_HEADERS,
            transport=transport,
        )

    async def __aenter__(self) -> "DuckDuckGoHtmlProvider":
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.client.aclose()

    async def search(self, query: str, limit: int) -> list[SearchResult]:
        try:
            response = await self.client.get(
                "https://html.duckduckgo.com/html/", params={"q": query}
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise SearchError("Search provider request failed") from exc
        encoding = response.encoding or "utf-8"
        try:
            html = response.content.decode(encoding, errors="replace")
        except LookupError:
            html = response.content.decode("utf-8", errors="replace")
        return parse_duckduckgo_html(html, limit)


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
    for block in soup.select(".result"):
        link = block.select_one("a.result__a")
        if link is None:
            continue
        title = link.get_text(" ", strip=True)
        href = link.get("href")
        if not title or not isinstance(href, str):
            continue
        snippet_node = block.select_one(".result__snippet")
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


def create_search_provider(name: str, timeout_seconds: float) -> SearchProvider:
    if name == "duckduckgo_html":
        return DuckDuckGoHtmlProvider(timeout_seconds)
    if name == "disabled":
        return DisabledSearchProvider()
    raise SearchError("Unsupported search provider")


async def search_web(
    provider_name: str, query: str, limit: int, timeout_seconds: float
) -> list[SearchResult]:
    provider = create_search_provider(provider_name, timeout_seconds)
    if isinstance(provider, DuckDuckGoHtmlProvider):
        async with provider:
            return await provider.search(query, limit)
    return await provider.search(query, limit)

