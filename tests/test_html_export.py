import gzip
from datetime import UTC, datetime

from app.fetchers.html_export import safe_html_filename, save_html


TIMESTAMP = datetime(2026, 6, 11, 12, 30, 45, tzinfo=UTC)


def test_safe_html_filename_uses_domain_and_timestamp() -> None:
    assert safe_html_filename("https://sub.example.com/page", TIMESTAMP) == (
        "sub.example.com_20260611_123045.html"
    )


def test_save_html_writes_plain_html(tmp_path) -> None:
    content = b"<html><body>Hello</body></html>"
    output = save_html(
        content,
        "https://example.com",
        tmp_path,
        compress_above_mb=5,
        minimum_free_mb=0,
        timestamp=TIMESTAMP,
    )

    assert output.parent == tmp_path / "html"
    assert output.suffix == ".html"
    assert output.read_bytes() == content


def test_save_html_compresses_large_content(tmp_path) -> None:
    content = b"<html>large</html>"
    output = save_html(
        content,
        "https://example.com",
        tmp_path,
        compress_above_mb=0,
        minimum_free_mb=0,
        timestamp=TIMESTAMP,
    )

    assert output.name.endswith(".html.gz")
    with gzip.open(output, "rb") as archive:
        assert archive.read() == content
