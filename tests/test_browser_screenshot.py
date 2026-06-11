from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.config import Settings
from app.fetchers.browser_screenshot import (
    ScreenshotOptions,
    ScreenshotResult,
    ScreenshotTooLargeError,
    screenshot_filename,
    validate_screenshot_size,
)


def test_screenshot_filename_uses_domain_and_timestamp() -> None:
    timestamp = datetime(2026, 6, 11, 12, 30, 45, tzinfo=UTC)
    assert screenshot_filename("https://sub.example.com/page", timestamp) == (
        "sub.example.com_20260611_123045.png"
    )


def test_screenshot_settings_parsing() -> None:
    settings = Settings(
        browser_timeout_seconds=30,
        screenshot_viewport_width=1440,
        screenshot_viewport_height=900,
        max_screenshot_size_mb=12,
    )

    assert settings.browser_timeout_seconds == 30
    assert settings.screenshot_viewport_width == 1440
    assert settings.screenshot_viewport_height == 900
    assert settings.max_screenshot_size_mb == 12


def test_screenshot_options_defaults() -> None:
    options = ScreenshotOptions()

    assert options.timeout_seconds == 45
    assert options.viewport_width == 1366
    assert options.viewport_height == 768
    assert options.max_size_mb == 20


def test_screenshot_size_limit_validation(tmp_path) -> None:
    screenshot = tmp_path / "page.png"
    screenshot.write_bytes(b"x" * 1100)

    with pytest.raises(ScreenshotTooLargeError, match="exceeds the 0.001 MB"):
        validate_screenshot_size(screenshot, 0.001)


def test_screenshot_result_model() -> None:
    result = ScreenshotResult(
        path=Path("downloads/screenshots/example.png"),
        filename="example.png",
        size_bytes=1234,
        final_url="https://example.com/final",
    )

    assert result.filename == "example.png"
    assert result.size_bytes == 1234
    assert result.final_url == "https://example.com/final"


@pytest.mark.skip(reason="Optional integration test requires installed Chromium")
def test_real_chromium_capture() -> None:
    pass
