import pytest

from app.search.providers import SearchResult
from app.search.service import (
    SearchQueryError,
    filter_safe_search_results,
    validate_search_query,
)


def test_query_validation_normalizes_whitespace() -> None:
    assert validate_search_query("  telegram   browser bot  ", 200) == (
        "telegram browser bot"
    )


@pytest.mark.parametrize("query", [None, "", "   "])
def test_query_validation_rejects_empty_query(query) -> None:
    with pytest.raises(SearchQueryError):
        validate_search_query(query, 200)


def test_query_validation_rejects_long_query() -> None:
    with pytest.raises(SearchQueryError, match="at most 5"):
        validate_search_query("123456", 5)


def test_private_and_invalid_search_urls_are_skipped() -> None:
    results = [
        SearchResult("Public", "https://example.com"),
        SearchResult("Localhost", "http://localhost/admin"),
        SearchResult("Private", "http://10.0.0.1/private"),
        SearchResult("File", "file:///tmp/data"),
        SearchResult("Script", "javascript:alert(1)"),
    ]

    assert filter_safe_search_results(results, 5) == [results[0]]

