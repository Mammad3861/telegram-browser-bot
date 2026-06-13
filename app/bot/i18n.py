from typing import Literal


Language = Literal["en", "fa"]
DEFAULT_LANGUAGE: Language = "en"
SUPPORTED_LANGUAGES = {"en", "fa"}

TEXTS: dict[str, dict[str, str]] = {
    "en": {
        "welcome": "Telegram Browser Bot is ready. Use /menu to get started.",
        "menu": "Choose an option or send a single http/https URL.",
        "help": (
            "Send a URL to open an action card, use /menu, or change language with "
            "/language. Search the web with /search.\n"
            "Advanced slash commands such as /fetch, /links, /html, /screenshot, "
            "and /pdf are still available."
        ),
        "open_url": "Send one http/https URL to create an action card.",
        "sessions": "No saved sessions. Use /cookies_import to add one.",
        "sessions_list": "Saved sessions:\n{sessions}",
        "account": (
            "Telegram ID: {user_id}\nAdmin: {admin}\nAccess: {access}\n"
            "Language: {language}"
        ),
        "yes": "yes",
        "no": "no",
        "about": (
            "Telegram Browser Bot\nVersion: {version}\n"
            "Interactive web export and browser automation for Telegram.\n"
            "Official runtime: {runtime_target}"
        ),
        "search_help": "Use /search your query to search the web.",
        "search_usage": "Usage: /search your query",
        "search_query_too_long": "Search query must be at most {max_length} characters.",
        "search_unavailable": "Search is temporarily unavailable. Please try again later.",
        "search_no_results": "No safe search results were found.",
        "search_results": "🔎 Results for: {query}",
        "search_expired": "This search session expired. Please search again.",
        "search_not_owned": "This search session belongs to another user.",
        "search_opening": "Opening result...",
        "search_closed": "Search results closed.",
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
            "یک نشانی بفرستید تا کارت عملیات ساخته شود، از /menu استفاده کنید، زبان را با /language تغییر دهید، یا با /search جست‌وجو کنید.\n"
            "دستورهای پیشرفته مانند /fetch، /links، /html، /screenshot و /pdf همچنان فعال هستند."
        ),
        "open_url": "یک نشانی http/https بفرستید تا کارت عملیات ساخته شود.",
        "sessions": "نشستی ذخیره نشده است. برای افزودن نشست از /cookies_import استفاده کنید.",
        "sessions_list": "نشست‌های ذخیره‌شده:\n{sessions}",
        "account": (
            "شناسه تلگرام: {user_id}\nمدیر: {admin}\nدسترسی: {access}\n"
            "زبان: {language}"
        ),
        "yes": "بله",
        "no": "خیر",
        "about": (
            "ربات مرورگر تلگرام\nنسخه: {version}\n"
            "ابزار تعاملی خروجی وب و مرورگر برای تلگرام.\n"
            "محیط رسمی: {runtime_target}"
        ),
        "search_help": "برای جست‌وجوی وب از /search عبارت موردنظر استفاده کنید.",
        "search_usage": "روش استفاده: /search عبارت جست‌وجو",
        "search_query_too_long": "عبارت جست‌وجو باید حداکثر {max_length} نویسه باشد.",
        "search_unavailable": "جست‌وجو موقتاً در دسترس نیست. بعداً دوباره تلاش کنید.",
        "search_no_results": "نتیجه امنی برای جست‌وجو پیدا نشد.",
        "search_results": "🔎 نتایج برای: {query}",
        "search_expired": "نشست جست‌وجو منقضی شده است. دوباره جست‌وجو کنید.",
        "search_not_owned": "این نشست جست‌وجو متعلق به کاربر دیگری است.",
        "search_opening": "در حال باز کردن نتیجه...",
        "search_closed": "نتایج جست‌وجو بسته شد.",
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
