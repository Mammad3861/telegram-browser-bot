from app.fetchers.link_extractor import LinkExtractor


def test_extracts_absolute_and_relative_links() -> None:
    html = """
    <a href="/about">About</a>
    <a href="https://other.example/page">Other</a>
    <a href="mailto:test@example.com">Email</a>
    <a href="/about">Duplicate</a>
    """

    assert LinkExtractor.extract(html, "https://example.com/docs/") == [
        "https://example.com/about",
        "https://other.example/page",
    ]
