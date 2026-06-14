import asyncio

import httpx
import pytest

from app.search.providers import (
    BraveSearchApiProvider,
    DisabledSearchProvider,
    DuckDuckGoHtmlProvider,
    SEARCH_PROVIDER_REGISTRY,
    SearchConfigurationError,
    SearchDisabledError,
    SearchError,
    SearchResult,
    SearxngSearchProvider,
    create_search_provider,
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


def test_provider_registry_selects_supported_providers() -> None:
    assert set(SEARCH_PROVIDER_REGISTRY) == {
        "disabled",
        "duckduckgo_html",
        "brave_api",
        "searxng",
    }
    assert isinstance(create_search_provider("disabled", 1), DisabledSearchProvider)
    assert isinstance(
        create_search_provider("duckduckgo_html", 1), DuckDuckGoHtmlProvider
    )


def test_disabled_provider_raises_specific_error() -> None:
    provider = create_search_provider("disabled", 1)

    with pytest.raises(SearchDisabledError):
        asyncio.run(provider.search("example", 5))


def test_brave_provider_requires_api_key() -> None:
    with pytest.raises(SearchConfigurationError):
        create_search_provider("brave_api", 1)


def test_searxng_provider_requires_base_url() -> None:
    with pytest.raises(SearchConfigurationError):
        create_search_provider("searxng", 1)


def test_brave_provider_parses_mocked_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Subscription-Token"] == "test-key"
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {
                            "title": "Example",
                            "url": "https://example.com",
                            "description": "Brave result",
                        }
                    ]
                }
            },
        )

    async def execute() -> list[SearchResult]:
        provider = BraveSearchApiProvider(
            "test-key", 1, transport=httpx.MockTransport(handler)
        )
        try:
            return await provider.search("example", 5)
        finally:
            await provider.aclose()

    assert asyncio.run(execute()) == [
        SearchResult("Example", "https://example.com", "Brave result", "brave_api")
    ]


def test_searxng_provider_parses_mocked_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["format"] == "json"
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "Example",
                        "url": "https://example.com",
                        "content": "SearxNG result",
                    }
                ]
            },
        )

    async def execute() -> list[SearchResult]:
        provider = SearxngSearchProvider(
            "https://search.example", 1, transport=httpx.MockTransport(handler)
        )
        try:
            return await provider.search("example", 5)
        finally:
            await provider.aclose()

    assert asyncio.run(execute()) == [
        SearchResult("Example", "https://example.com", "SearxNG result", "searxng")
    ]
