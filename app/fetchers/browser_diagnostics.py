import logging


BROWSER_INSTALL_MESSAGE = (
    "Chromium is not installed. Run: python -m playwright install chromium"
)


def is_browser_not_installed(error: BaseException) -> bool:
    message = str(error).lower()
    return "executable doesn't exist" in message or "browser executable" in message


def generic_browser_message(operation: str) -> str:
    return (
        f"{operation} failed in the browser. "
        "Try again or run on the supported Linux/Docker environment."
    )


def log_safe_browser_error(
    logger: logging.Logger, error: BaseException, safe_message: str
) -> None:
    logger.warning(
        "Browser operation failed: exception_type=%s safe_message=%s",
        type(error).__name__,
        safe_message,
    )
