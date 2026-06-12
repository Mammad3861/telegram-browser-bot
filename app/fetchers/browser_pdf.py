import asyncio
import ipaddress
import logging
import re
import socket
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.core.storage import ensure_free_space
from app.core.url_validation import URLValidationError, validate_url
from app.fetchers.browser_context import create_isolated_context
from app.fetchers.browser_diagnostics import (
    BROWSER_INSTALL_MESSAGE,
    generic_browser_message,
    is_browser_not_installed,
    log_safe_browser_error,
)


logger = logging.getLogger(__name__)


class PdfError(RuntimeError):
    pass


class PdfBrowserNotInstalledError(PdfError):
    pass


class PdfTimeoutError(PdfError):
    pass


class PdfTooLargeError(PdfError):
    pass


@dataclass(frozen=True)
class PdfOptions:
    timeout_seconds: float = 45.0
    format: str = "A4"
    print_background: bool = True
    max_size_mb: int = 30
    minimum_free_mb: int = 512
    cookies: tuple[dict, ...] = ()


@dataclass(frozen=True)
class PdfResult:
    path: Path
    filename: str
    size_bytes: int
    final_url: str


def pdf_filename(url: str, timestamp: datetime | None = None) -> str:
    hostname = urlparse(url).hostname or "page"
    safe_domain = re.sub(r"[^a-zA-Z0-9.-]+", "_", hostname).strip("._-") or "page"
    created_at = timestamp or datetime.now(UTC)
    return f"{safe_domain}_{created_at.strftime('%Y%m%d_%H%M%S')}.pdf"


def validate_pdf_size(path: Path, max_size_mb: int | float) -> int:
    size = path.stat().st_size
    if size > max_size_mb * 1024 * 1024:
        raise PdfTooLargeError(f"PDF exceeds the {max_size_mb} MB size limit")
    return size


async def _validate_browser_target(url: str) -> None:
    validate_url(url)
    hostname = urlparse(url).hostname
    if not hostname:
        raise URLValidationError("URL must include a hostname")
    try:
        addresses = await asyncio.get_running_loop().getaddrinfo(
            hostname, None, type=socket.SOCK_STREAM
        )
    except socket.gaierror as exc:
        raise PdfError("Hostname could not be resolved") from exc
    if any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise URLValidationError(
            "Hostname resolves to a private or non-public IP address"
        )


async def export_pdf(url: str, output_dir: Path, options: PdfOptions) -> PdfResult:
    url = validate_url(url)
    pdf_dir = output_dir / "pdf"
    ensure_free_space(pdf_dir, options.minimum_free_mb)
    output_path = pdf_dir / pdf_filename(url)
    timeout_ms = int(options.timeout_seconds * 1000)

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                context = await create_isolated_context(browser, options.cookies)
                page = await context.new_page()

                async def validate_route(route) -> None:
                    try:
                        await _validate_browser_target(route.request.url)
                    except (URLValidationError, PdfError):
                        await route.abort("blockedbyclient")
                        return
                    await route.continue_()

                await page.route("http://**/*", validate_route)
                await page.route("https://**/*", validate_route)
                response = await page.goto(
                    url, wait_until="domcontentloaded", timeout=timeout_ms
                )
                if response is None:
                    raise PdfError("Navigation failed without a response")
                if response.status >= 400:
                    raise PdfError(
                        f"The site blocked or rejected navigation with HTTP {response.status}"
                    )
                final_url = page.url
                await _validate_browser_target(final_url)
                await page.pdf(
                    path=output_path,
                    format=options.format,
                    print_background=options.print_background,
                )
            finally:
                await browser.close()
    except PlaywrightTimeoutError as exc:
        message = "Browser navigation timed out"
        log_safe_browser_error(logger, exc, message)
        raise PdfTimeoutError(message) from exc
    except URLValidationError:
        raise
    except PlaywrightError as exc:
        if is_browser_not_installed(exc):
            log_safe_browser_error(logger, exc, BROWSER_INSTALL_MESSAGE)
            raise PdfBrowserNotInstalledError(BROWSER_INSTALL_MESSAGE) from exc
        message = generic_browser_message("PDF export")
        log_safe_browser_error(logger, exc, message)
        raise PdfError(message) from exc

    size = validate_pdf_size(output_path, options.max_size_mb)
    return PdfResult(
        path=output_path,
        filename=output_path.name,
        size_bytes=size,
        final_url=final_url,
    )
