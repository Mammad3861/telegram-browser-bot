from typing import Literal


Language = Literal["en", "fa"]
DEFAULT_LANGUAGE: Language = "en"
SUPPORTED_LANGUAGES = {"en", "fa"}

TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "welcome": "Telegram Browser Bot is ready. Use /menu to get started.",
        "menu": "Choose an option or send a single http/https URL.",
        "help": (
            "Send a URL to open an action card, or use /menu.\n"
            "Advanced slash commands such as /fetch, /links, /html, /screenshot, "
            "and /pdf are still available."
        ),
        "open_url": "Send one http/https URL to create an action card.",
        "sessions": "Use /sessions to view encrypted browser sessions.",
        "account": "Telegram ID: {user_id}\nLanguage: {language}",
        "search_planned": "Search is planned for a future version.",
        "url_card": "URL action card\n\n{url}\n\nChoose an action:",
        "url_refreshed": "URL action card refreshed.\n\n{url}\n\nChoose an action:",
        "url_cancelled": "URL session cancelled.",
        "session_expired": "This URL session expired. Please send the URL again.",
        "session_not_owned": "This URL session belongs to another user.",
        "access_denied": "Access denied. Ask the bot owner for access.",
        "invalid_url": "Please send a single valid public http/https URL.",
        "language_current": "Current language: {language}\nAvailable: en, fa",
        "language_updated": "Language updated to {language}.",
        "language_usage": "Usage: /language en or /language fa",
        "job_started": "Job ID: {job_id}\nStatus: {status}",
        "no_links": "No links found.",
        "request_failed": "Request failed: {error}",
    },
    "fa": {
        "welcome": "ربات مرورگر تلگرام آماده است. برای شروع از /menu استفاده کنید.",
        "menu": "یک گزینه را انتخاب کنید یا یک نشانی http/https بفرستید.",
        "help": (
            "یک نشانی بفرستید تا کارت عملیات ساخته شود، یا از /menu استفاده کنید.\n"
            "دستورهای پیشرفته مانند /fetch، /links، /html، /screenshot و /pdf همچنان فعال هستند."
        ),
        "open_url": "یک نشانی http/https بفرستید تا کارت عملیات ساخته شود.",
        "sessions": "برای دیدن نشست‌های رمزگذاری‌شده از /sessions استفاده کنید.",
        "account": "شناسه تلگرام: {user_id}\nزبان: {language}",
        "search_planned": "جست‌وجوی وب برای نسخه آینده برنامه‌ریزی شده است.",
        "url_card": "کارت عملیات نشانی\n\n{url}\n\nیک عملیات را انتخاب کنید:",
        "url_refreshed": "کارت عملیات تازه‌سازی شد.\n\n{url}\n\nیک عملیات را انتخاب کنید:",
        "url_cancelled": "نشست این نشانی لغو شد.",
        "session_expired": "نشست این نشانی منقضی شده است. لطفاً نشانی را دوباره بفرستید.",
        "session_not_owned": "این نشست متعلق به کاربر دیگری است.",
        "access_denied": "دسترسی رد شد. از مالک ربات درخواست دسترسی کنید.",
        "invalid_url": "لطفاً فقط یک نشانی معتبر و عمومی http/https بفرستید.",
        "language_current": "زبان فعلی: {language}\nگزینه‌ها: en, fa",
        "language_updated": "زبان به {language} تغییر کرد.",
        "language_usage": "روش استفاده: /language en یا /language fa",
        "job_started": "شناسه کار: {job_id}\nوضعیت: {status}",
        "no_links": "پیوندی پیدا نشد.",
        "request_failed": "درخواست ناموفق بود: {error}",
    },
}

_preferences: dict[int, Language] = {}


def get_language(user_id: int | None) -> Language:
    if user_id is None:
        return DEFAULT_LANGUAGE
    return _preferences.get(user_id, DEFAULT_LANGUAGE)


def set_language(user_id: int, language: str) -> Language:
    normalized = language.strip().lower()
    if normalized not in SUPPORTED_LANGUAGES:
        raise ValueError("Unsupported language")
    selected: Language = normalized  # type: ignore[assignment]
    _preferences[user_id] = selected
    return selected


def clear_language_preferences() -> None:
    _preferences.clear()


def text(key: str, locale: str = DEFAULT_LANGUAGE, **values: object) -> str:
    selected = locale if locale in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    template = TEXTS.get(selected, {}).get(key) or TEXTS[DEFAULT_LANGUAGE].get(key, key)
    return template.format(**values)
