import asyncio
import ipaddress
import logging
import socket
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import async_playwright

from app.core.content_policy import validate_configured_policy
from app.core.url_validation import URLValidationError
from app.fetchers.browser_context import create_isolated_context


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InteractiveElement:
    index: int
    label: str
    kind: str
    href: str | None = None


@dataclass(frozen=True)
class InteractionResult:
    final_url: str
    title: str | None
    storage_state: dict[str, Any] | None


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


def option_label(element: InteractiveElement, current_url: str) -> str:
    kind = "link" if element.kind == "link" else "button"
    if element.href:
        current_domain = urlparse(current_url).hostname
        target_domain = urlparse(element.href).hostname
        if target_domain and target_domain != current_domain:
            return f"{element.label} · {kind} · {target_domain}"
    return f"{element.label} · {kind}"


async def extract_page_links(
    url: str,
    timeout_seconds: float,
    cookies: tuple[dict, ...] = (),
    proxy_server: str | None = None,
    storage_state: dict[str, Any] | None = None,
) -> list[str]:
    await _validate_target(url)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, proxy={"server": proxy_server} if proxy_server else None
        )
        try:
            context = await create_isolated_context(
                browser, cookies, storage_state=storage_state
            )
            page = await context.new_page()
            await page.goto(
                url, wait_until="domcontentloaded", timeout=int(timeout_seconds * 1000)
            )
            values = await page.locator("a[href]").evaluate_all(
                "els => els.filter(e => e.offsetParent !== null).map(e => e.href)"
            )
            links: list[str] = []
            for value in values:
                if not isinstance(value, str) or value in links:
                    continue
                try:
                    links.append(await _validate_target(value))
                except (URLValidationError, ValueError, OSError):
                    continue
                if len(links) >= 50:
                    break
            return links
        finally:
            await browser.close()


async def extract_interactive_elements(
    url: str,
    timeout_seconds: float,
    max_elements: int,
    cookies: tuple[dict, ...] = (),
    proxy_server: str | None = None,
    storage_state: dict[str, Any] | None = None,
) -> list[InteractiveElement]:
    await _validate_target(url)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, proxy={"server": proxy_server} if proxy_server else None
        )
        try:
            context = await create_isolated_context(
                browser, cookies, storage_state=storage_state
            )
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=int(timeout_seconds * 1000))
            items = await page.locator(
                "a[href], button, input[type=submit], input[type=button], [role=button]"
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
    storage_state: dict[str, Any] | None = None,
) -> InteractionResult:
    await _validate_target(url)
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(
            headless=True, proxy={"server": proxy_server} if proxy_server else None
        )
        try:
            context = await create_isolated_context(
                browser, cookies, storage_state=storage_state
            )
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=int(timeout_seconds * 1000))
            if await page.locator("input[type=password]").count():
                raise PermissionError("Password form interaction is not supported")
            if element.kind == "link" and element.href:
                await _validate_target(element.href)
                await page.goto(
                    element.href,
                    wait_until="domcontentloaded",
                    timeout=int(timeout_seconds * 1000),
                )
            else:
                locator = page.locator(
                    "a[href], button, input[type=submit], input[type=button], [role=button]"
                ).nth(element.index)
                await locator.click(timeout=int(timeout_seconds * 1000))
                try:
                    await page.wait_for_load_state(
                        "domcontentloaded", timeout=min(int(timeout_seconds * 1000), 5000)
                    )
                except PlaywrightTimeoutError:
                    pass
            await page.wait_for_timeout(500)
            final_url = await _validate_target(page.url)
            try:
                saved_state = await context.storage_state()
            except Exception as exc:
                logger.warning(
                    "Browser storage state capture failed: exception_type=%s",
                    type(exc).__name__,
                )
                saved_state = None
            return InteractionResult(
                final_url=final_url,
                title=await page.title() or None,
                storage_state=saved_state,
            )
        finally:
            await browser.close()
