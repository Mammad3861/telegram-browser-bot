import logging

from app.fetchers.browser_diagnostics import (
    BROWSER_INSTALL_MESSAGE,
    generic_browser_message,
    is_browser_not_installed,
    log_safe_browser_error,
)


def test_browser_not_installed_mapping() -> None:
    error = RuntimeError("Executable doesn't exist at /private/path")

    assert is_browser_not_installed(error)
    assert "playwright install chromium" in BROWSER_INSTALL_MESSAGE


def test_generic_browser_message_mentions_supported_runtime() -> None:
    message = generic_browser_message("Screenshot capture")

    assert "Screenshot capture failed" in message
    assert "Linux/Docker" in message


def test_safe_browser_log_does_not_include_original_error(caplog) -> None:
    logger = logging.getLogger("browser-diagnostics-test")

    with caplog.at_level(logging.WARNING):
        log_safe_browser_error(
            logger,
            RuntimeError("secret cookie value"),
            "Browser operation failed safely",
        )

    assert "RuntimeError" in caplog.text
    assert "Browser operation failed safely" in caplog.text
    assert "secret cookie value" not in caplog.text
