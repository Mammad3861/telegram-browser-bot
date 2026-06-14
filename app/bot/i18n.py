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
        "menu_open_url": "Open URL",
        "menu_sessions": "Sessions",
        "menu_account": "Account",
        "menu_help": "Help",
        "menu_search": "Search Web",
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
        "search_again_button": "Search again",
        "close_button": "Close",
        "url_card": "URL action card\n\n{url}\n\nChoose an action:",
        "url_refreshed": "URL action card refreshed.\n\n{url}\n\nChoose an action:",
        "url_cancelled": "URL session cancelled.",
        "url_screenshot_button": "Screenshot",
        "url_pdf_button": "PDF",
        "url_html_button": "HTML",
        "url_rendered_html_button": "Rendered HTML",
        "url_links_button": "Links",
        "url_download_button": "Download",
        "url_refresh_button": "Refresh",
        "url_cancel_button": "Cancel",
        "session_expired": "This URL session expired. Please send the URL again.",
        "session_not_owned": "This URL session belongs to another user.",
        "access_denied": "Access denied. Ask the bot owner for access.",
        "invalid_url": "Please send a single valid public http/https URL.",
        "language_current": "Current language: {language}\nAvailable: en, fa",
        "language_updated": "Language updated to {language}.",
        "language_usage": "Usage: /language en or /language fa",
        "job_started": "Job ID: {job_id}\nStatus: {status}",
        "job_id_label": "Job ID",
        "command_label": "Command",
        "status_label": "Status",
        "progress_label": "Progress",
        "result_label": "Result",
        "error_label": "Error",
        "domain_label": "Domain",
        "job_status_pending": "pending",
        "job_status_running": "running",
        "job_status_success": "success",
        "job_status_failed": "failed",
        "job_status_cancelled": "cancelled",
        "job_failed": "Job {job_id} failed: {error}",
        "job_not_found": "Job not found.",
        "no_jobs": "No jobs found.",
        "job_cancelled": "Job {job_id} cancelled.",
        "job_cancel_failed": "Job not found, not active, or not owned by you.",
        "status_usage": "Usage: /status <job_id>",
        "cancel_usage": "Usage: /cancel <job_id>",
        "url_usage": "Usage: /{command} https://example.com",
        "daily_quota_exceeded": "Daily download quota exceeded. Try again tomorrow.",
        "no_links": "No links found.",
        "request_failed": "Request failed: {error}",
        "admin_required": "Admin access required.",
        "whoami": "Your Telegram ID: {user_id}",
        "user_id_unavailable": "User ID unavailable.",
        "access_status": (
            "Your Telegram ID: {user_id}\nAdmin: {admin}\n"
            "Runtime access management: {runtime_state}\n"
            "Static allowed users: {static_count}\nRuntime allowed users: {runtime_count}"
        ),
        "enabled": "enabled",
        "disabled": "disabled",
        "runtime_access_disabled": "Runtime access management is disabled.",
        "access_target_required": "Telegram ID is required.",
        "access_target_invalid": "Telegram ID must be an integer.",
        "access_granted": "Access granted to {user_id}.",
        "access_already_allowed": "User {user_id} is already runtime-allowed.",
        "access_revoked": "Runtime access revoked for {user_id}.",
        "access_user_not_found": "Runtime allowed user not found.",
        "admin_cannot_be_denied": "Administrators cannot be denied access.",
        "allowed_users_list": (
            "Static allowed users: {static_users}\nRuntime allowed users:\n{runtime_users}"
        ),
        "none": "none",
        "cleanup_failed": "Cleanup failed because generated files could not be removed.",
        "cleanup_summary": "Cleanup complete.\nDeleted files: {count}\nFreed bytes: {bytes}",
        "purge_history_failed": "Job history could not be cleared.",
        "purge_history_summary": "Job history cleared. Removed entries: {count}",
        "invalid_action": "Invalid action.",
        "admin_status": (
            "Version: {version}\nRuntime target: {runtime_target}\nActive jobs: {active_jobs}\n"
            "Known jobs: {known_jobs}\nRuntime allowed users: {runtime_users}\n"
            "Storage free: {free_bytes} bytes\nCookie import: {cookie_state}\n"
            "Generated directories: {directories}"
        ),
        "ready": "ready",
        "missing": "missing",
        "cookies_help": (
            "Use /cookies_import <domain>, then send a Playwright-compatible JSON list. "
            "Each cookie requires name, value, and domain. Cookie values are never echoed."
        ),
        "cookie_import_disabled": "Cookie import is disabled.",
        "cookie_key_missing": (
            "Cookie encryption key is not configured. Ask the bot owner to configure it."
        ),
        "cookies_import_usage": "Usage: /cookies_import <domain>",
        "user_identification_failed": "Unable to identify the requesting user.",
        "cookies_send_json": "Send the JSON cookie list for {domain} in your next message.",
        "cookies_saved": "Cookies saved for {domain}.",
        "delete_session_usage": "Usage: /delete_session <domain>",
        "session_deleted": "Session deleted for {domain}.",
        "session_not_found": "Session not found.",
        "http_status": "Status: {status}",
        "filename_label": "Filename",
        "content_type_label": "Content type",
        "size_label": "Size",
        "final_url_label": "Final URL",
        "compressed_label": "Compressed",
        "sha256_label": "SHA256",
        "html_sent": "HTML saved and sent: {filename}",
        "rendered_html_sent": "Rendered HTML exported and sent: {filename}",
        "download_sent": "File downloaded and sent: {filename}",
        "screenshot_sent": "Screenshot captured and sent: {filename}",
        "pdf_sent": "PDF exported and sent: {filename}",
        "upload_limit_exceeded": "File saved locally but exceeds the Telegram upload limit.",
        "upload_limit_result": "File saved locally; Telegram upload limit exceeded.",
        "telegram_upload_failed": "Telegram could not accept the upload. The file remains saved locally.",
        "telegram_rendered_html_failed": "Telegram could not send the rendered HTML file.",
        "telegram_screenshot_failed": "Telegram could not send the screenshot file.",
        "telegram_pdf_failed": "Telegram could not send the PDF file.",
        "browser_request_failed": "Browser request failed.",
        "job_unexpected_failure": "Job failed unexpectedly.",
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
        "menu_open_url": "باز کردن نشانی",
        "menu_sessions": "نشست‌ها",
        "menu_account": "حساب",
        "menu_help": "راهنما",
        "menu_search": "جست‌وجوی وب",
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
        "search_again_button": "جست‌وجوی دوباره",
        "close_button": "بستن",
        "url_card": "کارت عملیات نشانی\n\n{url}\n\nیک عملیات را انتخاب کنید:",
        "url_refreshed": "کارت عملیات تازه‌سازی شد.\n\n{url}\n\nیک عملیات را انتخاب کنید:",
        "url_cancelled": "نشست این نشانی لغو شد.",
        "url_screenshot_button": "تصویر",
        "url_pdf_button": "PDF",
        "url_html_button": "HTML",
        "url_rendered_html_button": "HTML رندرشده",
        "url_links_button": "پیوندها",
        "url_download_button": "دانلود",
        "url_refresh_button": "تازه‌سازی",
        "url_cancel_button": "لغو",
        "session_expired": "نشست این نشانی منقضی شده است. لطفاً نشانی را دوباره بفرستید.",
        "session_not_owned": "این نشست متعلق به کاربر دیگری است.",
        "access_denied": "دسترسی رد شد. از مالک ربات درخواست دسترسی کنید.",
        "invalid_url": "لطفاً فقط یک نشانی معتبر و عمومی http/https بفرستید.",
        "language_current": "زبان فعلی: {language}\nگزینه‌ها: en, fa",
        "language_updated": "زبان به {language} تغییر کرد.",
        "language_usage": "روش استفاده: /language en یا /language fa",
        "job_started": "شناسه کار: {job_id}\nوضعیت: {status}",
        "job_id_label": "شناسه کار",
        "command_label": "دستور",
        "status_label": "وضعیت",
        "progress_label": "پیشرفت",
        "result_label": "نتیجه",
        "error_label": "خطا",
        "domain_label": "دامنه",
        "job_status_pending": "در انتظار",
        "job_status_running": "در حال اجرا",
        "job_status_success": "موفق",
        "job_status_failed": "ناموفق",
        "job_status_cancelled": "لغوشده",
        "job_failed": "کار {job_id} ناموفق بود: {error}",
        "job_not_found": "کار پیدا نشد.",
        "no_jobs": "کاری پیدا نشد.",
        "job_cancelled": "کار {job_id} لغو شد.",
        "job_cancel_failed": "کار پیدا نشد، فعال نیست یا متعلق به شما نیست.",
        "status_usage": "روش استفاده: /status <job_id>",
        "cancel_usage": "روش استفاده: /cancel <job_id>",
        "url_usage": "روش استفاده: /{command} https://example.com",
        "daily_quota_exceeded": "سهمیه روزانه دانلود تمام شده است. فردا دوباره تلاش کنید.",
        "no_links": "پیوندی پیدا نشد.",
        "request_failed": "درخواست ناموفق بود: {error}",
        "admin_required": "دسترسی مدیر لازم است.",
        "whoami": "شناسه تلگرام شما: {user_id}",
        "user_id_unavailable": "شناسه کاربر در دسترس نیست.",
        "access_status": (
            "شناسه تلگرام شما: {user_id}\nمدیر: {admin}\n"
            "مدیریت دسترسی زمان اجرا: {runtime_state}\n"
            "کاربران مجاز ثابت: {static_count}\nکاربران مجاز زمان اجرا: {runtime_count}"
        ),
        "enabled": "فعال",
        "disabled": "غیرفعال",
        "runtime_access_disabled": "مدیریت دسترسی زمان اجرا غیرفعال است.",
        "access_target_required": "شناسه تلگرام لازم است.",
        "access_target_invalid": "شناسه تلگرام باید عدد صحیح باشد.",
        "access_granted": "دسترسی به کاربر {user_id} داده شد.",
        "access_already_allowed": "کاربر {user_id} از قبل در فهرست مجاز است.",
        "access_revoked": "دسترسی زمان اجرای کاربر {user_id} لغو شد.",
        "access_user_not_found": "کاربر مجاز زمان اجرا پیدا نشد.",
        "admin_cannot_be_denied": "نمی‌توان دسترسی مدیران را لغو کرد.",
        "allowed_users_list": (
            "کاربران مجاز ثابت: {static_users}\nکاربران مجاز زمان اجرا:\n{runtime_users}"
        ),
        "none": "هیچ‌کدام",
        "cleanup_failed": "پاک‌سازی ناموفق بود و فایل‌های تولیدشده حذف نشدند.",
        "cleanup_summary": "پاک‌سازی کامل شد.\nفایل‌های حذف‌شده: {count}\nفضای آزادشده: {bytes} بایت",
        "purge_history_failed": "تاریخچه کارها پاک نشد.",
        "purge_history_summary": "تاریخچه کارها پاک شد. ورودی‌های حذف‌شده: {count}",
        "invalid_action": "عملیات نامعتبر است.",
        "admin_status": (
            "نسخه: {version}\nمحیط اجرا: {runtime_target}\nکارهای فعال: {active_jobs}\n"
            "کارهای شناخته‌شده: {known_jobs}\nکاربران مجاز زمان اجرا: {runtime_users}\n"
            "فضای آزاد: {free_bytes} بایت\nورود کوکی: {cookie_state}\n"
            "پوشه‌های خروجی: {directories}"
        ),
        "ready": "آماده",
        "missing": "ناموجود",
        "cookies_help": (
            "از /cookies_import <domain> استفاده کنید و سپس فهرست JSON سازگار با Playwright را بفرستید. "
            "هر کوکی باید name، value و domain داشته باشد. مقدار کوکی‌ها نمایش داده نمی‌شود."
        ),
        "cookie_import_disabled": "ورود کوکی غیرفعال است.",
        "cookie_key_missing": "کلید رمزنگاری کوکی تنظیم نشده است. از مالک ربات بخواهید آن را تنظیم کند.",
        "cookies_import_usage": "روش استفاده: /cookies_import <domain>",
        "user_identification_failed": "شناسایی کاربر درخواست‌کننده ممکن نشد.",
        "cookies_send_json": "فهرست JSON کوکی‌های دامنه {domain} را در پیام بعدی بفرستید.",
        "cookies_saved": "کوکی‌های دامنه {domain} ذخیره شد.",
        "delete_session_usage": "روش استفاده: /delete_session <domain>",
        "session_deleted": "نشست دامنه {domain} حذف شد.",
        "session_not_found": "نشست پیدا نشد.",
        "http_status": "وضعیت: {status}",
        "filename_label": "نام فایل",
        "content_type_label": "نوع محتوا",
        "size_label": "اندازه",
        "final_url_label": "نشانی نهایی",
        "compressed_label": "فشرده‌شده",
        "sha256_label": "SHA256",
        "html_sent": "HTML ذخیره و ارسال شد: {filename}",
        "rendered_html_sent": "HTML رندرشده صادر و ارسال شد: {filename}",
        "download_sent": "فایل دانلود و ارسال شد: {filename}",
        "screenshot_sent": "تصویر صفحه گرفته و ارسال شد: {filename}",
        "pdf_sent": "PDF صادر و ارسال شد: {filename}",
        "upload_limit_exceeded": "فایل محلی ذخیره شد اما از محدودیت ارسال تلگرام بزرگ‌تر است.",
        "upload_limit_result": "فایل محلی ذخیره شد؛ محدودیت ارسال تلگرام رد شد.",
        "telegram_upload_failed": "تلگرام فایل را نپذیرفت. فایل به‌صورت محلی باقی مانده است.",
        "telegram_rendered_html_failed": "تلگرام نتوانست فایل HTML رندرشده را ارسال کند.",
        "telegram_screenshot_failed": "تلگرام نتوانست فایل تصویر را ارسال کند.",
        "telegram_pdf_failed": "تلگرام نتوانست فایل PDF را ارسال کند.",
        "browser_request_failed": "درخواست مرورگر ناموفق بود.",
        "job_unexpected_failure": "کار به‌طور غیرمنتظره ناموفق بود.",
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
