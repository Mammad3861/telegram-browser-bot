from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.config import Settings
from app.fetchers.browser_pdf import (
    PdfOptions,
    PdfResult,
    PdfTooLargeError,
    pdf_filename,
    validate_pdf_size,
)


def test_pdf_filename_uses_domain_and_timestamp() -> None:
    timestamp = datetime(2026, 6, 12, 9, 15, 30, tzinfo=UTC)
    assert pdf_filename("https://sub.example.com/page", timestamp) == (
        "sub.example.com_20260612_091530.pdf"
    )


def test_pdf_settings_parsing() -> None:
    settings = Settings(
        max_pdf_size_mb=25,
        pdf_format="Letter",
        pdf_print_background="false",
    )

    assert settings.max_pdf_size_mb == 25
    assert settings.pdf_format == "Letter"
    assert settings.pdf_print_background is False


def test_pdf_options_defaults() -> None:
    options = PdfOptions()

    assert options.timeout_seconds == 45
    assert options.format == "A4"
    assert options.print_background is True
    assert options.max_size_mb == 30


def test_pdf_size_limit_validation(tmp_path) -> None:
    pdf = tmp_path / "page.pdf"
    pdf.write_bytes(b"x" * 1100)

    with pytest.raises(PdfTooLargeError, match="exceeds the 0.001 MB"):
        validate_pdf_size(pdf, 0.001)


def test_pdf_result_model() -> None:
    result = PdfResult(
        path=Path("downloads/pdf/example.pdf"),
        filename="example.pdf",
        size_bytes=2048,
        final_url="https://example.com/final",
    )

    assert result.filename == "example.pdf"
    assert result.size_bytes == 2048
    assert result.final_url == "https://example.com/final"


@pytest.mark.skip(reason="Optional integration test requires installed Chromium")
def test_real_chromium_pdf_export() -> None:
    pass
