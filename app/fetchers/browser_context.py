from typing import Any


async def create_isolated_context(
    browser: Any,
    cookies: tuple[dict, ...] = (),
    viewport: dict[str, int] | None = None,
    storage_state: dict[str, Any] | None = None,
) -> Any:
    options = {"viewport": viewport} if viewport else {}
    if storage_state:
        options["storage_state"] = storage_state
    context = await browser.new_context(**options)
    if cookies:
        await context.add_cookies(list(cookies))
    return context
