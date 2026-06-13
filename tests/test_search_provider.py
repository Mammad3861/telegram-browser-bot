import asyncio

import httpx
import pytest

from app.search.providers import (
    DuckDuckGoHtmlProvider,
    SearchError,
    SearchResult,
    parse_duckduckgo_html,
)


def test_search_result_model() -> None:
    result = SearchResult(
        title="Example",
        url="https://example.com",
        snippet="Example snippet",
        source="test",
    )

    assert result.title == "Example"
    assert result.source == "test"


def test_parses_duckduckgo_html_results() -> None:
    html = """
    <div class="result">
      <a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage">Example</a>
      <a class="result__snippet">A useful result.</a>
    </div>
    """

    results = parse_duckduckgo_html(html, limit=5)

    assert results == [
        SearchResult(
            title="Example",
            url="https://example.com/page",
            snippet="A useful result.",
            source="duckduckgo_html",
        )
    ]


def test_provider_failure_maps_to_search_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    async def execute() -> None:
        async with DuckDuckGoHtmlProvider(
            timeout_seconds=1,
            transport=httpx.MockTransport(handler),
        ) as provider:
            await provider.search("example", 5)

    with pytest.raises(SearchError, match="provider request failed"):
        asyncio.run(execute())

