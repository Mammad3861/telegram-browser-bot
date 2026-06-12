import gzip
from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.config import Settings
from app.fetchers.browser_html import (
    RenderedHtmlOptions,
    RenderedHtmlResult,
    rendered_html_filename,
    save_rendered_html,
)


TIMESTAMP = datetime(2026, 6, 12, 10, 20, 30, tzinfo=UTC)


def test_rendered_html_options_defaults() -> None:
    options = RenderedHtmlOptions()

    assert options.timeout_seconds == 45
    assert options.max_html_size_mb == 5
    assert options.wait_until == "domcontentloaded"
    assert options.viewport_width == 1366
    assert options.viewport_height == 768


def test_rendered_html_settings_parsing() -> None:
    settings = Settings(rendered_html_wait_until="load")

    assert settings.rendered_html_wait_until == "load"


def test_rendered_html_result_model() -> None:
    result = RenderedHtmlResult(
        path=Path("downloads/html_rendered/example.html"),
        filename="example.html",
        size_bytes=123,
        final_url="https://example.com/final",
        compressed=False,
    )

    assert result.filename == "example.html"
    assert result.size_bytes == 123
    assert result.compressed is False


def test_rendered_html_filename() -> None:
    assert rendered_html_filename("https://sub.example.com/page", TIMESTAMP) == (
        "sub.example.com_20260612_102030.html"
    )


def test_save_rendered_html_plain(tmp_path) -> None:
    content = b"<html><body>rendered</body></html>"
    path, compressed = save_rendered_html(
        content, "https://example.com", tmp_path, 5, TIMESTAMP
    )

    assert compressed is False
    assert path.suffix == ".html"
    assert path.read_bytes() == content


def test_save_rendered_html_compressed(tmp_path) -> None:
    content = b"<html><body>rendered</body></html>"
    path, compressed = save_rendered_html(
        content, "https://example.com", tmp_path, 0, TIMESTAMP
    )

    assert compressed is True
    assert path.name.endswith(".html.gz")
    with gzip.open(path, "rb") as archive:
        assert archive.read() == content


@pytest.mark.skip(reason="Optional integration test requires installed Chromium")
def test_real_chromium_rendered_html_export() -> None:
    pass
