from pathlib import Path
from typing import Literal

from app.config import get_settings
from app.core.bot_text_store import get_bot_text
from app.core.preference_store import get_user_language, set_user_language


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
        "search_unavailable": (
            "Search is temporarily unavailable. Try again later or send a direct URL."
        ),
        "search_disabled": "Web search is disabled. You can still send a direct URL.",
        "search_misconfigured": (
            "Search is not configured correctly. Please contact the bot owner or send a direct URL."
        ),
        "search_no_results": (
            "No safe results were found. Try different words or send a direct URL."
        ),
        "search_source": "Source: {provider}",
        "search_partial_results": "Showing {count} of up to {requested} requested results.",
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
        "admin_required": "Admin access required.",
        "texts_overview": (
            "Editable text keys: welcome, help, about\nLanguages: en, fa\n"
            "Use /set_text, /reset_text, and /preview_text."
        ),
        "text_updated": "Updated {key}/{language}.",
        "text_reset": "Reset {target} to default.",
        "text_override_missing": "No override found for {target}.",
        "text_preview": "Preview {key}/{language}:\n\n{preview}",
        "text_invalid_key": "Invalid text key. Use welcome, help, or about.",
        "text_invalid_language": "Invalid language. Use en or fa.",
        "text_too_long": "Text is too long. Maximum length is {max_length} characters.",
        "text_empty": "Text cannot be empty.",
        "text_key_required": "Text key is required.",
        "set_text_usage": "Usage: /set_text <key> <lang> <text>",
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
        "search_unavailable": (
            "جست‌وجو موقتاً در دسترس نیست. بعداً دوباره تلاش کنید یا یک نشانی مستقیم بفرستید."
        ),
        "search_disabled": "جست‌وجوی وب غیرفعال است. همچنان می‌توانید یک نشانی مستقیم بفرستید.",
        "search_misconfigured": (
            "جست‌وجو درست پیکربندی نشده است. با مالک ربات تماس بگیرید یا یک نشانی مستقیم بفرستید."
        ),
        "search_no_results": (
            "نتیجه امنی پیدا نشد. عبارت دیگری امتحان کنید یا یک نشانی مستقیم بفرستید."
        ),
        "search_source": "منبع: {provider}",
        "search_partial_results": "{count} نتیجه از حداکثر {requested} نتیجه درخواستی نمایش داده می‌شود.",
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
        "admin_required": "دسترسی مدیر لازم است.",
        "texts_overview": (
            "کلیدهای متن قابل ویرایش: welcome, help, about\nزبان‌ها: en, fa\n"
            "از /set_text، /reset_text و /preview_text استفاده کنید."
        ),
        "text_updated": "متن {key}/{language} به‌روزرسانی شد.",
        "text_reset": "متن {target} به مقدار پیش‌فرض بازنشانی شد.",
        "text_override_missing": "برای {target} متن سفارشی پیدا نشد.",
        "text_preview": "پیش‌نمایش {key}/{language}:\n\n{preview}",
        "text_invalid_key": "کلید متن نامعتبر است. از welcome، help یا about استفاده کنید.",
        "text_invalid_language": "زبان نامعتبر است. از en یا fa استفاده کنید.",
        "text_too_long": "متن بیش از حد طولانی است. حداکثر طول {max_length} نویسه است.",
        "text_empty": "متن نمی‌تواند خالی باشد.",
        "text_key_required": "کلید متن لازم است.",
        "set_text_usage": "روش استفاده: /set_text <key> <lang> <text>",
    },
}

def get_language(user_id: int | None, path: Path | None = None) -> Language:
    if user_id is None:
        return DEFAULT_LANGUAGE
    target = path or Path(get_settings().user_preferences_path)
    language = get_user_language(target, user_id, DEFAULT_LANGUAGE)
    return language if language in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE  # type: ignore[return-value]


def set_language(
    user_id: int, language: str, path: Path | None = None
) -> Language:
    normalized = language.strip().lower()
    if normalized not in SUPPORTED_LANGUAGES:
        raise ValueError("Unsupported language")
    selected: Language = normalized  # type: ignore[assignment]
    target = path or Path(get_settings().user_preferences_path)
    set_user_language(target, user_id, selected)
    return selected


def clear_language_preferences(path: Path | None = None) -> None:
    target = path or Path(get_settings().user_preferences_path)
    try:
        target.unlink()
    except FileNotFoundError:
        pass


def text(message_key: str, locale: str = DEFAULT_LANGUAGE, **values: object) -> str:
    selected = locale if locale in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    template = TEXTS.get(selected, {}).get(message_key) or TEXTS[DEFAULT_LANGUAGE].get(
        message_key, message_key
    )
    return template.format(**values)


def bot_text(key: str, locale: str = DEFAULT_LANGUAGE, **values: object) -> str:
    override = get_bot_text(Path(get_settings().bot_texts_path), key, locale)
    if override is not None:
        return override
    return text(key, locale, **values)
