from datetime import UTC, datetime

from app.fetchers.file_detector import (
    choose_filename,
    content_disposition_filename,
    is_direct_file,
    sanitize_filename,
)


def test_detects_file_from_url_extension() -> None:
    assert is_direct_file("https://example.com/report.pdf", "text/html", None)


def test_detects_file_from_content_type() -> None:
    assert is_direct_file("https://example.com/get?id=1", "application/pdf", None)


def test_normal_html_page_is_not_a_direct_file() -> None:
    assert not is_direct_file("https://example.com/page", "text/html; charset=utf-8", None)
    assert not is_direct_file(
        "https://example.com/file.exe", "application/octet-stream", None
    )


def test_extracts_filename_from_content_disposition() -> None:
    header = 'attachment; filename="quarterly report.pdf"'
    assert content_disposition_filename(header) == "quarterly report.pdf"
    assert choose_filename("https://example.com/file", header) == "quarterly report.pdf"


def test_sanitizes_unsafe_filename() -> None:
    assert sanitize_filename('bad<>:"|?*.pdf') == "bad_______.pdf"
    assert sanitize_filename("CON.pdf") == "_CON.pdf"


def test_filename_falls_back_to_timestamp() -> None:
    timestamp = datetime(2026, 6, 11, 12, 30, 45, tzinfo=UTC)
    assert choose_filename("https://example.com/", None, timestamp) == (
        "downloaded_file_20260611_123045"
    )
