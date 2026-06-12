import asyncio
from unittest.mock import AsyncMock

from app.fetchers.browser_context import create_isolated_context


def test_browser_context_receives_cookies() -> None:
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
