import asyncio
import ipaddress
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


class ScreenshotError(RuntimeError):
    pass


class BrowserNotInstalledError(ScreenshotError):
    pass


class ScreenshotTimeoutError(ScreenshotError):
    pass


class ScreenshotTooLargeError(ScreenshotError):
    pass


@dataclass(frozen=True)
class ScreenshotOptions:
    timeout_seconds: float = 45.0
    viewport_width: int = 1366
    viewport_height: int = 768
    max_size_mb: int = 20
    minimum_free_mb: int = 512
    cookies: tuple[dict, ...] = ()


@dataclass(frozen=True)
class ScreenshotResult:
    path: Path
    filename: str
    size_bytes: int
    final_url: str


def screenshot_filename(url: str, timestamp: datetime | None = None) -> str:
    hostname = urlparse(url).hostname or "page"
    safe_domain = re.sub(r"[^a-zA-Z0-9.-]+", "_", hostname).strip("._-") or "page"
    created_at = timestamp or datetime.now(UTC)
    return f"{safe_domain}_{created_at.strftime('%Y%m%d_%H%M%S')}.png"


def validate_screenshot_size(path: Path, max_size_mb: int) -> int:
    size = path.stat().st_size
    if size > max_size_mb * 1024 * 1024:
        raise ScreenshotTooLargeError(
            f"Screenshot exceeds the {max_size_mb} MB size limit"
        )
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
        raise ScreenshotError("Hostname could not be resolved") from exc
    if any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise URLValidationError(
            "Hostname resolves to a private or non-public IP address"
        )


async def capture_screenshot(
    url: str, output_dir: Path, options: ScreenshotOptions
) -> ScreenshotResult:
    url = validate_url(url)
    screenshots_dir = output_dir / "screenshots"
    ensure_free_space(screenshots_dir, options.minimum_free_mb)
    output_path = screenshots_dir / screenshot_filename(url)
    timeout_ms = int(options.timeout_seconds * 1000)

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            try:
                context = await create_isolated_context(
                    browser,
                    options.cookies,
                    {
                        "width": options.viewport_width,
                        "height": options.viewport_height,
                    },
                )
                page = await context.new_page()

                async def validate_route(route) -> None:
                    try:
                        await _validate_browser_target(route.request.url)
                    except (URLValidationError, ScreenshotError):
                        await route.abort("blockedbyclient")
                        return
                    await route.continue_()

                await page.route("http://**/*", validate_route)
                await page.route("https://**/*", validate_route)
                response = await page.goto(
                    url, wait_until="domcontentloaded", timeout=timeout_ms
                )
                if response is None:
                    raise ScreenshotError("Navigation failed without a response")
                if response.status >= 400:
                    raise ScreenshotError(
                        f"The site blocked or rejected navigation with HTTP {response.status}"
                    )
                final_url = page.url
                await _validate_browser_target(final_url)
                await page.screenshot(path=output_path, full_page=True, type="png")
            finally:
                await browser.close()
    except PlaywrightTimeoutError as exc:
        raise ScreenshotTimeoutError("Browser navigation timed out") from exc
    except URLValidationError:
        raise
    except PlaywrightError as exc:
        error_text = str(exc).lower()
        if "executable doesn't exist" in error_text or "browser executable" in error_text:
            raise BrowserNotInstalledError(
                "Chromium is not installed. Run: python -m playwright install chromium"
            ) from exc
        raise ScreenshotError("Browser navigation failed") from exc

    size = validate_screenshot_size(output_path, options.max_size_mb)
    return ScreenshotResult(
        path=output_path,
        filename=output_path.name,
        size_bytes=size,
        final_url=final_url,
    )
