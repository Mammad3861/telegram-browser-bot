from typing import Any


async def create_isolated_context(
    browser: Any,
    cookies: tuple[dict, ...] = (),
    viewport: dict[str, int] | None = None,
) -> Any:
    options = {"viewport": viewport} if viewport else {}
    context = await browser.new_context(**options)
    if cookies:
        await context.add_cookies(list(cookies))
    return context
