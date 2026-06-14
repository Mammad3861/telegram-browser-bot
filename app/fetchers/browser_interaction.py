import asyncio
import ipaddress
import socket
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright

from app.core.content_policy import validate_configured_policy
from app.core.url_validation import URLValidationError
from app.fetchers.browser_context import create_isolated_context


@dataclass(frozen=True)
class InteractiveElement:
    index: int
    label: str
    kind: str
    href: str | None = None


async def _validate_target(url: str) -> str:
    try:
        validated = validate_configured_policy(url)
    except ValueError as exc:
        raise URLValidationError(str(exc)) from exc
    hostname = urlparse(validated).hostname or ""
    addresses = await asyncio.get_running_loop().getaddrinfo(
        hostname, None, type=socket.SOCK_STREAM
    )
    if any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise URLValidationError("Private or non-public destination")
    return validated


def normalize_elements(items: list[dict], base_url: str, limit: int) -> list[InteractiveElement]:
    elements: list[InteractiveElement] = []
    for item in items:
        label = " ".join(str(item.get("label", "")).split())[:80]
        kind = str(item.get("kind", "button"))
        href = item.get("href")
        if not label or kind not in {"link", "button"}:
            continue
        if isinstance(href, str) and href:
            href = urljoin(base_url, href)
        else:
            href = None
        elements.append(
            InteractiveElement(int(item.get("index", len(elements))), label, kind, href)
        )
        if len(elements) >= limit:
            break
    return elements


async def extract_interactive_elements(
    url: str,
    timeout_seconds: float,
    max_elements: int,
    cookies: tuple[dict, ...] = (),
    proxy_server: str | None = None,
) -> list[InteractiveElement]:
    await _validate_target(url)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, proxy={"server": proxy_server} if proxy_server else None
        )
        try:
            context = await create_isolated_context(browser, cookies)
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=int(timeout_seconds * 1000))
            items = await page.locator(
                "a[href], button, input[type=submit], [role=button]"
            ).evaluate_all(
                """els => els.map((e, index) => {
                  const s = getComputedStyle(e); const r = e.getBoundingClientRect();
                  return {e, index, visible: s.visibility !== 'hidden' && s.display !== 'none' && r.width > 0 && r.height > 0};
                }).filter(item => item.visible).map(({e, index}) => ({
                  label: (e.innerText || e.value || e.getAttribute('aria-label') || '').trim(),
                  kind: e.tagName === 'A' ? 'link' : 'button',
                  href: e.tagName === 'A' ? e.href : null,
                  index
                }))"""
            )
            return normalize_elements(items, page.url, max_elements)
        finally:
            await browser.close()


async def activate_interactive_element(
    url: str,
    element: InteractiveElement,
    timeout_seconds: float,
    cookies: tuple[dict, ...] = (),
    proxy_server: str | None = None,
) -> tuple[str, str | None]:
    if element.kind == "link" and element.href:
        return await _validate_target(element.href), None
    await _validate_target(url)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, proxy={"server": proxy_server} if proxy_server else None
        )
        try:
            context = await create_isolated_context(browser, cookies)
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=int(timeout_seconds * 1000))
            if await page.locator("input[type=password]").count():
                raise PermissionError("Password form interaction is not supported")
            locator = page.locator(
                "a[href], button, input[type=submit], [role=button]"
            ).nth(element.index)
            await locator.click(timeout=int(timeout_seconds * 1000))
            await page.wait_for_timeout(500)
            final_url = await _validate_target(page.url)
            return final_url, await page.title()
        finally:
            await browser.close()
