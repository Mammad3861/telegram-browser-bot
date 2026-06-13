from app.core.url_validation import URLValidationError, validate_url
from app.search.providers import SearchResult


class SearchQueryError(ValueError):
    pass


def validate_search_query(query: str | None, max_length: int) -> str:
    if query is None or not query.strip():
        raise SearchQueryError("Search query is required")
    normalized = " ".join(query.split())
    if len(normalized) > max_length:
        raise SearchQueryError(f"Search query must be at most {max_length} characters")
    return normalized


def filter_safe_search_results(
    results: list[SearchResult], limit: int
) -> list[SearchResult]:
    safe: list[SearchResult] = []
    for result in results:
        try:
            validate_url(result.url)
        except URLValidationError:
            continue
        safe.append(result)
        if len(safe) >= limit:
            break
    return safe

