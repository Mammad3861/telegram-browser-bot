import asyncio
import gzip
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


class RenderedHtmlError(RuntimeError):
    pass


class RenderedHtmlBrowserNotInstalledError(RenderedHtmlError):
    pass


class RenderedHtmlTimeoutError(RenderedHtmlError):
    pass


@dataclass(frozen=True)
class RenderedHtmlOptions:
    timeout_seconds: float = 45.0
    max_html_size_mb: int = 5
    wait_until: str = "domcontentloaded"
    viewport_width: int = 1366
    viewport_height: int = 768
    minimum_free_mb: int = 512
    cookies: tuple[dict, ...] = ()


@dataclass(frozen=True)
class RenderedHtmlResult:
    path: Path
    filename: str
    size_bytes: int
    final_url: str
    compressed: bool


def rendered_html_filename(url: str, timestamp: datetime | None = None) -> str:
    hostname = urlparse(url).hostname or "page"
    safe_domain = re.sub(r"[^a-zA-Z0-9.-]+", "_", hostname).strip("._-") or "page"
    created_at = timestamp or datetime.now(UTC)
    return f"{safe_domain}_{created_at.strftime('%Y%m%d_%H%M%S')}.html"


def save_rendered_html(
    content: bytes,
    url: str,
    output_dir: Path,
    max_html_size_mb: int | float,
    timestamp: datetime | None = None,
) -> tuple[Path, bool]:
    output_path = output_dir / rendered_html_filename(url, timestamp)
    compressed = len(content) > max_html_size_mb * 1024 * 1024
    if compressed:
        output_path = output_path.with_suffix(".html.gz")
        with gzip.open(output_path, "wb") as archive:
            archive.write(content)
    else:
        output_path.write_bytes(content)
    return output_path, compressed


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
        raise RenderedHtmlError("Hostname could not be resolved") from exc
    if any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise URLValidationError(
            "Hostname resolves to a private or non-public IP address"
        )


async def export_rendered_html(
    url: str, output_dir: Path, options: RenderedHtmlOptions
) -> RenderedHtmlResult:
    url = validate_url(url)
    rendered_dir = output_dir / "html_rendered"
    ensure_free_space(rendered_dir, options.minimum_free_mb)
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
                    except (URLValidationError, RenderedHtmlError):
                        await route.abort("blockedbyclient")
                        return
                    await route.continue_()

                await page.route("http://**/*", validate_route)
                await page.route("https://**/*", validate_route)
                response = await page.goto(
                    url, wait_until=options.wait_until, timeout=timeout_ms
                )
                if response is None:
                    raise RenderedHtmlError("Navigation failed without a response")
                if response.status >= 400:
                    raise RenderedHtmlError(
                        f"The site blocked or rejected navigation with HTTP {response.status}"
                    )
                final_url = page.url
                await _validate_browser_target(final_url)
                content = (await page.content()).encode("utf-8")
            finally:
                await browser.close()
    except PlaywrightTimeoutError as exc:
        raise RenderedHtmlTimeoutError("Browser navigation timed out") from exc
    except URLValidationError:
        raise
    except PlaywrightError as exc:
        error_text = str(exc).lower()
        if "executable doesn't exist" in error_text or "browser executable" in error_text:
            raise RenderedHtmlBrowserNotInstalledError(
                "Chromium is not installed. Run: python -m playwright install chromium"
            ) from exc
        raise RenderedHtmlError("Rendered HTML export failed during browser navigation") from exc

    output_path, compressed = save_rendered_html(
        content, final_url, rendered_dir, options.max_html_size_mb
    )
    return RenderedHtmlResult(
        path=output_path,
        filename=output_path.name,
        size_bytes=output_path.stat().st_size,
        final_url=final_url,
        compressed=compressed,
    )
