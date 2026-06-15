import asyncio
from unittest.mock import AsyncMock

from app.fetchers.browser_context import create_isolated_context


def test_browser_context_receives_cookies_and_viewport() -> None:
    context = AsyncMock()
    browser = AsyncMock()
    browser.new_context.return_value = context
    cookies = ({"name": "session", "value": "secret", "domain": "example.com"},)

    result = asyncio.run(
        create_isolated_context(browser, cookies, {"width": 1366, "height": 768})
    )

    assert result is context
    browser.new_context.assert_awaited_once_with(
        viewport={"width": 1366, "height": 768}
    )
    context.add_cookies.assert_awaited_once_with(list(cookies))


class FakeContext:
    def __init__(self) -> None:
        self.cookies = []

    async def add_cookies(self, cookies) -> None:
        self.cookies.extend(cookies)


class FakeBrowser:
    def __init__(self) -> None:
        self.options = None
        self.context = FakeContext()

    async def new_context(self, **options):
        self.options = options
        return self.context


def test_browser_context_loads_storage_state_and_existing_cookies() -> None:
    browser = FakeBrowser()
    storage_state = {"cookies": [], "origins": []}
    cookies = ({"name": "session", "value": "value", "domain": "example.com"},)

    context = asyncio.run(
        create_isolated_context(browser, cookies, storage_state=storage_state)
    )

    assert context is browser.context
    assert browser.options == {"storage_state": storage_state}
    assert browser.context.cookies == list(cookies)
