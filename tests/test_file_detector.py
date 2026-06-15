from datetime import UTC, datetime

from app.fetchers.file_detector import (
    choose_filename,
    content_disposition_filename,
    is_direct_file,
    detect_file,
    looks_like_download_link,
    sanitize_filename,
)


def test_detects_file_from_url_extension() -> None:
    assert is_direct_file("https://example.com/report.pdf", None, None)
    assert not is_direct_file("https://example.com/report.pdf", "text/html", None)
    assert detect_file("https://example.com/report.pdf", "text/html").confidence == "verify"


def test_detects_file_from_content_type() -> None:
    assert is_direct_file("https://example.com/get?id=1", "application/pdf", None)


def test_normal_html_page_is_not_a_direct_file() -> None:
    assert not is_direct_file("https://example.com/page", "text/html; charset=utf-8", None)
    assert is_direct_file("https://example.com/file.exe", "application/octet-stream", None)


def test_detects_installer_url_extensions() -> None:
    assert is_direct_file("https://example.com/putty-installer.msi", None, None)


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


def test_content_disposition_attachment_is_confident() -> None:
    detection = detect_file(
        "https://example.com/export",
        "application/octet-stream",
        'attachment; filename="archive.zip"',
    )

    assert detection.confident
    assert detection.reason == "content_disposition"


def test_direct_media_files_are_allowed_but_manifests_are_not() -> None:
    assert is_direct_file("https://files.example.com/audio.mp3")
    assert is_direct_file("https://files.example.com/video.mp4")
    assert not is_direct_file("https://files.example.com/master.m3u8")
    assert not is_direct_file("https://files.example.com/manifest.mpd")


def test_download_discovery_finds_files_and_ignores_stream_manifests() -> None:
    assert looks_like_download_link("https://example.com/files/manual.pdf")
    assert looks_like_download_link("https://example.com/get?id=1&download=1")
    assert not looks_like_download_link("https://example.com/master.m3u8", "Download")
