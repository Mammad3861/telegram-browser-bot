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
        "welcome": "Telegram Browser\nSend a URL or search the web.",
        "menu": "Telegram Browser\nSend a URL or search the web.",
        "menu_open_url": "Open URL",
        "menu_sessions": "Sessions",
        "menu_account": "Account",
        "menu_help": "Help",
        "menu_search": "Search Web",
        "menu_new_url": "New URL",
        "menu_recent_jobs": "Recent jobs",
        "menu_language": "Language",
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
        "url_card": "Browser tab\n{title}\n{url}\n\nChoose an action:",
        "url_refreshed": "Browser tab updated.\n{title}\n{url}\n\nChoose an action:",
        "url_cancelled": "URL session cancelled.",
        "url_screenshot_button": "Screenshot",
        "url_pdf_button": "PDF",
        "url_html_button": "HTML",
        "url_rendered_html_button": "Rendered HTML",
        "url_links_button": "Links",
        "url_download_button": "Download",
        "url_find_downloads_button": "Find downloads",
        "url_refresh_button": "Refresh",
        "url_cancel_button": "Cancel",
        "url_back_button": "Back",
        "url_interact_button": "Page options",
        "search_input_prompt": "Send your search text.",
        "url_input_prompt": "Send one public http/https URL.",
        "send_url_or_search": "Send a valid URL or use the Search button.",
        "interaction_choose": "Selectable page options:",
        "interaction_none": "No selectable page options were found.",
        "interaction_failed": "The page option could not be applied. Try another action.",
        "direct_file_only": "This version only supports direct file links.",
        "interaction_expired": "These page options expired. Open Page options again.",
        "page_option_applied": "The option was selected and the page was updated.",
        "page_state_not_saved": "The option was selected, but page state could not be saved. The page may show the same prompt again.",
        "tab_back_unavailable": "There is no previous page in this tab.",
        "commands_refresh_success": "Telegram command menus were refreshed. Client caching may delay updates.",
        "commands_refresh_failed": "Telegram command menus could not be refreshed.",
        "debug_commands": "Registered command menu summary:\n{commands}",
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
            "Version: {version}\nRuntime target: {runtime_target}\nUptime: {uptime_seconds}s\n"
            "Downloads directory: {downloads_dir}\nStorage free: {free_bytes}\n"
            "Active jobs: {active_jobs}\nKnown jobs: {known_jobs}\nRecent completed jobs: {recent_completed_jobs}\n"
            "URL sessions: {url_sessions}\nSearch sessions: {search_sessions}\nBrowser tab sessions: {browser_tab_sessions}\n"
            "Runtime allowed users: {runtime_users}\nCookie import: {cookie_state}\n"
            "Content policy: {policy_state}\nSearch provider: {search_provider}\n"
            "Command menu mode: {command_menu_mode}\nDownload mode: {download_mode}\n"
            "Cleanup: {cleanup_hours}h, after-send {cleanup_after_send}\n"
            "Browser features: {browser_state}\nGenerated directories: {directories}"
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
        "content_policy_blocked": "This site is blocked by the bot content policy.",
        "protected_media_download": "Direct downloads from streaming platforms or protected content are not supported. If you have an authorized direct file link, send that file link instead.",
        "download_uncertain": (
            "⚠️ This link was not confidently detected as a direct file.\n"
            "Content type: {content_type}\nApproximate size: {size}\nFinal URL: {final_url}\n\n"
            "If you trust the source, you can confirm a download attempt.\n\n{risk}"
        ),
        "download_risk_acceptance": "By confirming, you state that you trust the link source and are authorized to receive this file.",
        "download_confirm_button": "Try download",
        "download_cancel_button": "Cancel",
        "download_admin_force_button": "Admin: force download",
        "download_confirmed": "Download attempt confirmed.",
        "download_cancelled": "Download cancelled.",
        "download_confirmation_expired": "This download confirmation expired. Try again.",
        "download_direct_accepted": "Direct file accepted ({reason}).",
        "download_discovery_title": "Downloadable files:",
        "download_discovery_none": "No downloadable files were found.",
        "download_discovery_disabled": "Download discovery is disabled.",
        "download_reason_content_disposition": "attachment filename",
        "download_reason_file_extension": "file extension",
        "download_reason_content_type": "content type",
        "download_reason_download_hint": "download hint",
        "download_reason_unknown_response": "unknown response",
        "download_reason_head_unavailable": "metadata unavailable",
        "unknown": "unknown",
        "media_site_note": (
            "Some media sites may not work fully inside the bot. Browser actions are limited "
            "to safe previews and exports."
        ),
        "proxy_not_configured": "Proxy route is not configured.",
        "policy_status": (
            "Content policy: {state}\nDefault action: {default_action}\n"
            "Built-in safety filter: {builtin_state}\n"
            "Blocked domains: {blocked}\nAllowed domains: {allowed}\n"
            "Blocked categories: {categories}\nAllowed categories: {allowed_categories}\n"
            "Configurable categories: {configurable_categories}\nUpdated: {updated_at}"
        ),
        "policy_domain_added": "Policy rule added for {domain}.",
        "policy_domain_exists": "Policy rule already exists for {domain}.",
        "policy_domain_removed": "Policy rule removed for {domain}.",
        "policy_domain_missing": "Policy rule was not found for {domain}.",
        "policy_test_result": "Policy test: {decision}\nReason: {reason}\nCategory: {category}",
        "policy_reloaded": "Content policy reloaded. Blocked domains: {count}.",
        "policy_usage_block": "Usage: /block_domain <domain> [category]",
        "policy_invalid_category": "Invalid category. Use: {categories}.",
        "policy_category_adult": "adult",
        "policy_category_gambling": "gambling",
        "policy_category_crypto": "crypto",
        "policy_category_malware": "malware",
        "policy_category_phishing": "phishing",
        "policy_category_dangerous": "dangerous",
        "policy_category_media": "media",
        "policy_category_custom": "custom",
        "policy_state_blocked": "blocked",
        "policy_state_allowed": "allowed",
        "policy_state_neutral": "neutral",
        "policy_categories_title": "Category policy:\n{categories}",
        "policy_category_line": "{category}: {state}",
        "policy_category_rule_updated": "{category} is now {state}.",
        "policy_category_rule_unchanged": "{category} was already {state}.",
        "policy_category_usage": "Usage: /{command} <category>",
        "policy_category_domain_usage": "Usage: /{command} <category> <domain>",
        "policy_category_domains": "Domains classified as {category}:\n{domains}",
        "policy_invalid_category_or_domain": "Invalid category or domain. Categories: {categories}.",
        "policy_category_domain_added": "Added {domain} to {category}.",
        "policy_category_domain_exists": "{domain} is already in {category}.",
        "policy_category_domain_removed": "Removed {domain} from {category}.",
        "policy_category_domain_missing": "{domain} was not found in {category}.",
        "policy_usage_domain": "Usage: /{command} <domain>",
        "policy_usage_test": "Usage: /policy_test <url>",
        "allowed": "allowed",
        "blocked": "blocked",
        "policy_reason_default_allow": "allowed by default",
        "policy_reason_default_block": "blocked by default",
        "policy_reason_blocked_category": "blocked by category",
        "policy_reason_allowed_category": "allowed by category",
        "policy_reason_blocked_domain": "blocked by domain rule",
        "policy_reason_explicitly_allowed": "allowed by domain rule",
        "policy_reason_policy_disabled": "content policy is disabled",
        "policy_reason_blocked_keyword": "blocked by keyword",
        "policy_reason_allowed_keyword": "allowed by keyword",
        "routes_status": "Routing profile: {profile}\nRules:\n{rules}",
        "route_rule_set": "Route for {domain} set to {route}.",
        "route_rule_removed": "Route rule removed for {domain}.",
        "route_rule_missing": "Route rule was not found for {domain}.",
        "route_test_result": "Route for {domain}: {route}",
        "route_default": "default",
        "route_proxy": "proxy",
        "route_no_rules": "No rules are configured.",
        "route_usage": "Usage: /route_domain <domain> <default|proxy>",
        "unroute_usage": "Usage: /unroute_domain <domain>",
        "route_test_usage": "Usage: /route_test <url>",
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
        "cleanup_dry_run_summary": (
            "Cleanup dry run complete.\nFiles that would be deleted: {count}\n"
            "Bytes that would be freed: {bytes}"
        ),
        "storage_summary": (
            "Storage summary\nDownloads directory: {downloads_dir}\nFree space: {free_bytes}\n"
            "Cleanup retention: {cleanup_hours} hours\n\n{categories}"
        ),
        "storage_category_line": "{category}: {bytes}",
        "setup_ok": "OK",
        "setup_attention": "needs attention",
        "setup_check": (
            "Setup check\n"
            "Bot token configured: {bot_token}\n"
            "Admin IDs configured: {admin_ids}\n"
            "Downloads writable: {downloads_writable}\n"
            "Persistent stores writable: {persistent_dirs}\n"
            "Free disk OK: {free_disk}\n"
            "Browser ready: {browser_ready}\n"
            "Search provider: {search_provider}\n"
            "Command menu mode: {command_menu_mode}\n"
            "Content policy: {content_policy}\n"
            "Cookie import: {cookie_import}\n"
            "Health readiness: {health_ready}"
        ),
        "rate_limited": "You are doing that too often. Try again in about {seconds} seconds.",
        "search_rate_limited": "Search limit reached. Try again in about {seconds} seconds.",
        "browser_rate_limited": "Browser action limit reached. Try again in about {seconds} seconds.",
        "job_status_expired": "expired",
        "job_retryable_hint": "\nThis may work if you try again later.",
        "error_timeout": "The request timed out.",
        "error_connect": "Could not connect to the remote site.",
        "error_http_403": "The site refused this request.",
        "error_http_404": "The page was not found.",
        "error_http_410": "The page is no longer available.",
        "error_http_429": "The site is rate-limiting requests.",
        "error_http_5xx": "The remote site returned a server error.",
        "error_file_too_large": "The file is too large for the configured limits.",
        "error_disk_low": "The server does not have enough free disk space.",
        "error_provider_unavailable": "The provider is unavailable. You can send a direct URL instead.",
        "error_browser_failed": "Browser rendering failed. Try again later or use a direct HTTP action.",
        "error_content_policy_blocked": "This request is blocked by the bot content policy.",
        "error_protected_media_blocked": "Protected media downloads are not supported.",
        "error_route_not_configured": "The selected outbound route is not configured.",
        "error_generic": "The request could not be completed safely.",
        "error_retryable_hint": " You can try again later.",
    },
    "fa": {
        "welcome": "مرورگر تلگرامی\nیک نشانی بفرستید یا جست‌وجو کنید.",
        "menu": "مرورگر تلگرامی\nیک نشانی بفرستید یا جست‌وجو کنید.",
        "menu_open_url": "باز کردن نشانی",
        "menu_sessions": "نشست‌ها",
        "menu_account": "حساب",
        "menu_help": "راهنما",
        "menu_search": "جست‌وجو",
        "menu_new_url": "تب جدید / نشانی جدید",
        "menu_recent_jobs": "کارهای اخیر",
        "menu_language": "زبان",
        "help": (
            "یک نشانی بفرستید یا از /menu جست‌وجو را شروع کنید. زبان را هم می‌توانید با /language تغییر دهید.\n"
            "دستورهای پیشرفته مثل /fetch، /links، /html، /screenshot و /pdf همچنان در دسترس‌اند."
        ),
        "open_url": "یک نشانی http/https بفرستید تا تب مرورگر باز شود.",
        "sessions": "نشستی ذخیره نشده است. برای افزودن نشست، از /cookies_import استفاده کنید.",
        "sessions_list": "نشست‌های ذخیره‌شده:\n{sessions}",
        "account": (
            "شناسه تلگرام: {user_id}\nمدیر: {admin}\nدسترسی: {access}\n"
            "زبان: {language}"
        ),
        "yes": "بله",
        "no": "خیر",
        "about": (
            "مرورگر تلگرامی\nنسخه: {version}\n"
            "مرور و دریافت خروجی از صفحه‌های وب در تلگرام.\n"
            "محیط اجرای رسمی: {runtime_target}"
        ),
        "search_help": "برای جست‌وجو بنویسید: /search عبارت موردنظر",
        "search_usage": "روش استفاده: /search عبارت جست‌وجو",
        "search_query_too_long": "عبارت جست‌وجو باید حداکثر {max_length} نویسه باشد.",
        "search_unavailable": (
            "جست‌وجو موقتاً در دسترس نیست. بعداً دوباره تلاش کنید یا یک نشانی مستقیم بفرستید."
        ),
        "search_disabled": "جست‌وجوی وب غیرفعال است. همچنان می‌توانید یک نشانی مستقیم بفرستید.",
        "search_misconfigured": (
            "جست‌وجو درست تنظیم نشده است. با مدیر بات تماس بگیرید یا یک نشانی مستقیم بفرستید."
        ),
        "search_no_results": (
            "نتیجه‌ای پیدا نشد. عبارت دیگری را امتحان کنید یا یک نشانی مستقیم بفرستید."
        ),
        "search_source": "منبع: {provider}",
        "search_partial_results": "از {requested} نتیجه درخواستی، {count} نتیجه نمایش داده شد.",
        "search_results": "🔎 نتایج جست‌وجو برای: {query}",
        "search_expired": "نشست جست‌وجو منقضی شده است. دوباره جست‌وجو کنید.",
        "search_not_owned": "این نشست جست‌وجو متعلق به کاربر دیگری است.",
        "search_opening": "در حال باز کردن نتیجه…",
        "search_closed": "نتایج جست‌وجو بسته شد.",
        "search_again_button": "جست‌وجوی دوباره",
        "close_button": "بستن",
        "url_card": "تب مرورگر\n{title}\n{url}\n\nچه کاری انجام شود؟",
        "url_refreshed": "تب به‌روزرسانی شد.\n{title}\n{url}\n\nچه کاری انجام شود؟",
        "url_cancelled": "نشست این نشانی لغو شد.",
        "url_screenshot_button": "تصویر صفحه",
        "url_pdf_button": "PDF",
        "url_html_button": "HTML",
        "url_rendered_html_button": "HTML رندرشده",
        "url_links_button": "لینک‌ها",
        "url_download_button": "دانلود",
        "url_find_downloads_button": "فایل‌های قابل دانلود",
        "url_refresh_button": "تازه‌سازی",
        "url_cancel_button": "لغو",
        "url_back_button": "بازگشت",
        "url_interact_button": "گزینه‌های صفحه",
        "search_input_prompt": "عبارت جست‌وجو را بفرستید.",
        "url_input_prompt": "یک نشانی عمومی http/https بفرستید.",
        "send_url_or_search": "یک نشانی معتبر بفرستید یا از دکمه جست‌وجو استفاده کنید.",
        "interaction_choose": "گزینه‌های قابل انتخاب صفحه:",
        "interaction_none": "گزینه‌ای پیدا نشد.",
        "interaction_failed": "گزینه صفحه اعمال نشد. گزینه دیگری را امتحان کنید.",
        "direct_file_only": "فقط لینک مستقیم فایل پشتیبانی می‌شود.",
        "interaction_expired": "این گزینه‌ها منقضی شده‌اند. دوباره گزینه‌های صفحه را باز کنید.",
        "page_option_applied": "گزینه انتخاب شد و صفحه به‌روزرسانی شد.",
        "page_state_not_saved": "گزینه انتخاب شد، اما ذخیره وضعیت صفحه ممکن نبود. ممکن است صفحه دوباره همان پیام را نشان دهد.",
        "tab_back_unavailable": "صفحه قبلی در این تب وجود ندارد.",
        "commands_refresh_success": "منوی دستورهای تلگرام تازه‌سازی شد. ممکن است تلگرام تغییرات را با کمی تأخیر نشان دهد.",
        "commands_refresh_failed": "منوی دستورهای تلگرام تازه‌سازی نشد.",
        "debug_commands": "خلاصه منوی دستورهای ثبت‌شده:\n{commands}",
        "session_expired": "نشست این نشانی منقضی شده است. لطفاً نشانی را دوباره بفرستید.",
        "session_not_owned": "این نشست متعلق به کاربر دیگری است.",
        "access_denied": "دسترسی ندارید. از مدیر بات درخواست دسترسی کنید.",
        "invalid_url": "لینک معتبر نیست. فقط یک نشانی عمومی http/https بفرستید.",
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
        "job_status_cancelled": "لغو شده",
        "job_failed": "کار {job_id} انجام نشد: {error}",
        "job_not_found": "کار پیدا نشد.",
        "no_jobs": "کاری پیدا نشد.",
        "job_cancelled": "کار {job_id} لغو شد.",
        "job_cancel_failed": "کار پیدا نشد، فعال نیست یا متعلق به شما نیست.",
        "status_usage": "روش استفاده: /status <job_id>",
        "cancel_usage": "روش استفاده: /cancel <job_id>",
        "url_usage": "روش استفاده: /{command} https://example.com",
        "daily_quota_exceeded": "سهمیه روزانه دانلود تمام شده است. فردا دوباره تلاش کنید.",
        "no_links": "لینکی پیدا نشد.",
        "request_failed": "درخواست انجام نشد: {error}",
        "admin_required": "این بخش فقط برای مدیران است.",
        "whoami": "شناسه تلگرام شما: {user_id}",
        "user_id_unavailable": "شناسه کاربر در دسترس نیست.",
        "access_status": (
            "شناسه تلگرام شما: {user_id}\nمدیر: {admin}\n"
            "مدیریت دسترسی پویا: {runtime_state}\n"
            "کاربران مجاز ثابت: {static_count}\nکاربران مجاز پویا: {runtime_count}"
        ),
        "enabled": "فعال",
        "disabled": "غیرفعال",
        "runtime_access_disabled": "مدیریت دسترسی پویا غیرفعال است.",
        "access_target_required": "شناسه تلگرام لازم است.",
        "access_target_invalid": "شناسه تلگرام باید عدد صحیح باشد.",
        "access_granted": "دسترسی به کاربر {user_id} داده شد.",
        "access_already_allowed": "کاربر {user_id} از قبل در فهرست مجاز است.",
        "access_revoked": "دسترسی کاربر {user_id} لغو شد.",
        "access_user_not_found": "کاربر در فهرست دسترسی پیدا نشد.",
        "admin_cannot_be_denied": "نمی‌توان دسترسی مدیران را لغو کرد.",
        "allowed_users_list": (
            "کاربران مجاز ثابت: {static_users}\nکاربران مجاز پویا:\n{runtime_users}"
        ),
        "none": "هیچ‌کدام",
        "cleanup_failed": "پاک‌سازی انجام نشد؛ فایل‌های تولیدشده حذف نشدند.",
        "cleanup_summary": "پاک‌سازی انجام شد.\nفایل‌های حذف‌شده: {count}\nفضای آزادشده: {bytes}",
        "purge_history_failed": "تاریخچه کارها پاک نشد.",
        "purge_history_summary": "تاریخچه کارها پاک شد. ورودی‌های حذف‌شده: {count}",
        "invalid_action": "عملیات نامعتبر است.",
        "admin_status": (
            "نسخه: {version}\nمحیط اجرا: {runtime_target}\nزمان اجرا: {uptime_seconds} ثانیه\n"
            "پوشه دانلودها: {downloads_dir}\nفضای آزاد: {free_bytes}\n"
            "کارهای فعال: {active_jobs}\nکارهای ثبت‌شده: {known_jobs}\nکارهای تکمیل‌شده اخیر: {recent_completed_jobs}\n"
            "نشست‌های URL: {url_sessions}\nنشست‌های جست‌وجو: {search_sessions}\nنشست‌های تب مرورگر: {browser_tab_sessions}\n"
            "کاربران مجاز پویا: {runtime_users}\nورود کوکی: {cookie_state}\n"
            "سیاست محتوا: {policy_state}\nارائه‌دهنده جست‌وجو: {search_provider}\n"
            "حالت منوی دستورها: {command_menu_mode}\nحالت دانلود: {download_mode}\n"
            "پاک‌سازی: {cleanup_hours} ساعت، پس از ارسال {cleanup_after_send}\n"
            "قابلیت‌های مرورگر: {browser_state}\nپوشه‌های خروجی: {directories}"
        ),
        "ready": "آماده",
        "missing": "ناموجود",
        "cookies_help": (
            "ابتدا /cookies_import <domain> را بفرستید، سپس فهرست JSON سازگار با Playwright را ارسال کنید. "
            "هر کوکی باید name، value و domain داشته باشد. مقدار کوکی‌ها نمایش داده نمی‌شود."
        ),
        "cookie_import_disabled": "واردکردن کوکی غیرفعال است.",
        "cookie_key_missing": "کلید رمزنگاری کوکی تنظیم نشده است. از مدیر بات بخواهید آن را تنظیم کند.",
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
        "html_sent": "فایل HTML آماده و ارسال شد: {filename}",
        "rendered_html_sent": "HTML رندرشده آماده و ارسال شد: {filename}",
        "download_sent": "فایل دانلود و ارسال شد: {filename}",
        "screenshot_sent": "تصویر صفحه گرفته و ارسال شد: {filename}",
        "pdf_sent": "PDF ساخته و ارسال شد: {filename}",
        "upload_limit_exceeded": "فایل محلی ذخیره شد اما از محدودیت ارسال تلگرام بزرگ‌تر است.",
        "upload_limit_result": "فایل روی سرور ذخیره شد، اما برای ارسال در تلگرام بیش از حد بزرگ است.",
        "telegram_upload_failed": "تلگرام فایل را نپذیرفت. فایل به‌صورت محلی باقی مانده است.",
        "telegram_rendered_html_failed": "تلگرام نتوانست فایل HTML رندرشده را ارسال کند.",
        "telegram_screenshot_failed": "تلگرام نتوانست فایل تصویر را ارسال کند.",
        "telegram_pdf_failed": "تلگرام نتوانست فایل PDF را ارسال کند.",
        "browser_request_failed": "مرورگر نتوانست صفحه را باز کند.",
        "job_unexpected_failure": "کار به‌دلیل یک خطای پیش‌بینی‌نشده انجام نشد.",
        "content_policy_blocked": "این سایت طبق سیاست محتوای بات مسدود شده است.",
        "protected_media_download": "دانلود مستقیم از پلتفرم‌های استریم یا محتوای محافظت‌شده پشتیبانی نمی‌شود. اگر لینک مستقیم و مجاز فایل را دارید، همان لینک فایل را بفرستید.",
        "download_uncertain": (
            "⚠️ این لینک با اطمینان به‌عنوان فایل مستقیم تشخیص داده نشد.\n"
            "نوع محتوا: {content_type}\nاندازه تقریبی: {size}\nنشانی نهایی: {final_url}\n\n"
            "اگر به منبع لینک اعتماد دارید، می‌توانید تلاش برای دانلود را تأیید کنید.\n\n{risk}"
        ),
        "download_risk_acceptance": "با تأیید، شما اعلام می‌کنید که به منبع لینک اعتماد دارید و مجاز به دریافت این فایل هستید.",
        "download_confirm_button": "تلاش برای دانلود",
        "download_cancel_button": "لغو",
        "download_admin_force_button": "مدیر: تلاش اجباری برای دانلود",
        "download_confirmed": "تلاش برای دانلود تأیید شد.",
        "download_cancelled": "دانلود لغو شد.",
        "download_confirmation_expired": "این تأیید دانلود منقضی شده است. دوباره تلاش کنید.",
        "download_direct_accepted": "فایل مستقیم پذیرفته شد ({reason}).",
        "download_discovery_title": "فایل‌های قابل دانلود:",
        "download_discovery_none": "فایل قابل دانلودی پیدا نشد.",
        "download_discovery_disabled": "یافتن فایل‌های قابل دانلود غیرفعال است.",
        "download_reason_content_disposition": "نام فایل پیوست",
        "download_reason_file_extension": "پسوند فایل",
        "download_reason_content_type": "نوع محتوا",
        "download_reason_download_hint": "نشانه دانلود",
        "download_reason_unknown_response": "پاسخ ناشناخته",
        "download_reason_head_unavailable": "اطلاعات فایل در دسترس نیست",
        "unknown": "نامشخص",
        "media_site_note": (
            "ممکن است برخی سایت‌های رسانه‌ای داخل بات کامل کار نکنند. امکانات مرورگر به "
            "پیش‌نمایش و خروجی‌های امن محدود است."
        ),
        "proxy_not_configured": "مسیر پراکسی تنظیم نشده است.",
        "policy_status": (
            "سیاست محتوا: {state}\nرفتار پیش‌فرض: {default_action}\n"
            "فهرست داخلی دسته‌بندی: {builtin_state}\n"
            "دامنه‌های مسدود دستی: {blocked}\nدامنه‌های مجاز دستی: {allowed}\n"
            "دسته‌های مسدود: {categories}\nدسته‌های مجاز: {allowed_categories}\n"
            "دسته‌های قابل تنظیم: {configurable_categories}\nآخرین تغییر: {updated_at}"
        ),
        "policy_domain_added": "قانون دامنه {domain} ثبت شد.",
        "policy_domain_exists": "قانون دامنه {domain} از قبل ثبت شده است.",
        "policy_domain_removed": "قانون دامنه {domain} حذف شد.",
        "policy_domain_missing": "قانونی برای دامنه {domain} پیدا نشد.",
        "policy_test_result": "نتیجه بررسی سیاست: {decision}\nدلیل: {reason}\nدسته: {category}",
        "policy_reloaded": "سیاست محتوا دوباره بارگذاری شد. دامنه‌های مسدود دستی: {count}.",
        "policy_usage_block": "روش استفاده: /block_domain <domain> [category]",
        "policy_invalid_category": "دسته نامعتبر است. دسته‌های معتبر: {categories}",
        "policy_category_adult": "بزرگسالان",
        "policy_category_gambling": "قمار",
        "policy_category_crypto": "کریپتو",
        "policy_category_malware": "بدافزار",
        "policy_category_phishing": "فیشینگ",
        "policy_category_dangerous": "خطرناک",
        "policy_category_media": "رسانه",
        "policy_category_custom": "سفارشی",
        "policy_state_blocked": "مسدود",
        "policy_state_allowed": "مجاز",
        "policy_state_neutral": "بدون محدودیت",
        "policy_categories_title": "سیاست دسته‌ها:\n{categories}",
        "policy_category_line": "{category}: {state}",
        "policy_category_rule_updated": "دسته {category} اکنون {state} است.",
        "policy_category_rule_unchanged": "دسته {category} از قبل {state} است.",
        "policy_category_usage": "روش استفاده: /{command} <category>",
        "policy_category_domain_usage": "روش استفاده: /{command} <category> <domain>",
        "policy_category_domains": "دامنه‌های دسته {category}:\n{domains}",
        "policy_invalid_category_or_domain": "دسته یا دامنه نامعتبر است. دسته‌های معتبر: {categories}",
        "policy_category_domain_added": "دامنه {domain} به دسته {category} افزوده شد.",
        "policy_category_domain_exists": "دامنه {domain} از قبل در دسته {category} وجود دارد.",
        "policy_category_domain_removed": "دامنه {domain} از دسته {category} حذف شد.",
        "policy_category_domain_missing": "دامنه {domain} در دسته {category} پیدا نشد.",
        "policy_usage_domain": "روش استفاده: /{command} <domain>",
        "policy_usage_test": "روش استفاده: /policy_test <url>",
        "allowed": "مجاز",
        "blocked": "مسدود",
        "policy_reason_default_allow": "مجاز طبق پیش‌فرض",
        "policy_reason_default_block": "مسدود طبق پیش‌فرض",
        "policy_reason_blocked_category": "مسدود به‌دلیل دسته",
        "policy_reason_allowed_category": "مجاز به‌دلیل دسته مجاز",
        "policy_reason_blocked_domain": "مسدود به‌دلیل دامنه",
        "policy_reason_explicitly_allowed": "مجاز به‌دلیل دامنه مجاز",
        "policy_reason_policy_disabled": "سیاست محتوا غیرفعال است",
        "policy_reason_blocked_keyword": "مسدود به‌دلیل عبارت ممنوع",
        "policy_reason_allowed_keyword": "مجاز به‌دلیل عبارت مجاز",
        "routes_status": "پروفایل مسیریابی: {profile}\nقانون‌ها:\n{rules}",
        "route_rule_set": "مسیر دامنه {domain} روی {route} تنظیم شد.",
        "route_rule_removed": "قانون مسیر {domain} حذف شد.",
        "route_rule_missing": "قانونی برای مسیر دامنه {domain} پیدا نشد.",
        "route_test_result": "مسیر دامنه {domain}: {route}",
        "route_default": "مسیر مستقیم",
        "route_proxy": "مسیر پراکسی",
        "route_no_rules": "قانونی ثبت نشده است.",
        "route_usage": "روش استفاده: /route_domain <domain> <default|proxy>",
        "unroute_usage": "روش استفاده: /unroute_domain <domain>",
        "route_test_usage": "روش استفاده: /route_test <url>",
        "texts_overview": (
            "متن‌های قابل ویرایش:\n"
            "- welcome — پیام خوش‌آمد\n- help — راهنما\n- about — درباره بات\n\n"
            "زبان‌ها:\n- fa — فارسی\n- en — انگلیسی\n\n"
            "برای تغییر متن از /set_text، برای بازنشانی از /reset_text و برای پیش‌نمایش از /preview_text استفاده کنید."
        ),
        "text_updated": "متن {key}/{language} به‌روز شد.",
        "text_reset": "متن {target} به حالت پیش‌فرض برگشت.",
        "text_override_missing": "برای {target} متن سفارشی پیدا نشد.",
        "text_preview": "پیش‌نمایش {key}/{language}:\n\n{preview}",
        "text_invalid_key": "کلید متن نامعتبر است. از welcome، help یا about استفاده کنید.",
        "text_invalid_language": "زبان نامعتبر است. از en یا fa استفاده کنید.",
        "text_too_long": "متن خیلی طولانی است. حداکثر {max_length} نویسه مجاز است.",
        "text_empty": "متن نمی‌تواند خالی باشد.",
        "text_key_required": "کلید متن لازم است.",
        "set_text_usage": "روش استفاده: /set_text <key> <lang> <text>",
        "cleanup_dry_run_summary": (
            "بررسی پاک‌سازی انجام شد.\nفایل‌هایی که حذف می‌شوند: {count}\n"
            "فضایی که آزاد می‌شود: {bytes}"
        ),
        "storage_summary": (
            "گزارش فضای ذخیره‌سازی\nپوشه دانلودها: {downloads_dir}\nفضای آزاد: {free_bytes}\n"
            "نگه‌داری پاک‌سازی: {cleanup_hours} ساعت\n\n{categories}"
        ),
        "storage_category_line": "{category}: {bytes}",
        "setup_ok": "تأیید شد",
        "setup_attention": "نیازمند بررسی",
        "setup_check": (
            "بررسی راه‌اندازی\n"
            "توکن بات: {bot_token}\n"
            "شناسه مدیران: {admin_ids}\n"
            "پوشه دانلودها: {downloads_writable}\n"
            "پوشه‌های داده پایدار: {persistent_dirs}\n"
            "فضای آزاد: {free_disk}\n"
            "مرورگر: {browser_ready}\n"
            "ارائه‌دهنده جست‌وجو: {search_provider}\n"
            "حالت منوی دستورها: {command_menu_mode}\n"
            "سیاست محتوا: {content_policy}\n"
            "ورود کوکی: {cookie_import}\n"
            "وضعیت سلامت: {health_ready}"
        ),
        "rate_limited": "این کار را بیش از حد سریع انجام می‌دهید. حدود {seconds} ثانیه دیگر دوباره تلاش کنید.",
        "search_rate_limited": "سقف جست‌وجو پر شده است. حدود {seconds} ثانیه دیگر دوباره تلاش کنید.",
        "browser_rate_limited": "سقف عملیات مرورگر پر شده است. حدود {seconds} ثانیه دیگر دوباره تلاش کنید.",
        "job_status_expired": "منقضی‌شده",
        "job_retryable_hint": "\nممکن است با تلاش دوباره در زمان بعدی انجام شود.",
        "error_timeout": "زمان درخواست تمام شد.",
        "error_connect": "اتصال به سایت مقصد ممکن نشد.",
        "error_http_403": "سایت این درخواست را نپذیرفت.",
        "error_http_404": "صفحه پیدا نشد.",
        "error_http_410": "صفحه دیگر در دسترس نیست.",
        "error_http_429": "سایت تعداد درخواست‌ها را محدود کرده است.",
        "error_http_5xx": "سایت مقصد خطای سرور برگرداند.",
        "error_file_too_large": "فایل از محدودیت‌های تنظیم‌شده بزرگ‌تر است.",
        "error_disk_low": "فضای آزاد سرور برای این کار کافی نیست.",
        "error_provider_unavailable": "ارائه‌دهنده در دسترس نیست. می‌توانید یک لینک مستقیم بفرستید.",
        "error_browser_failed": "رندر مرورگر انجام نشد. بعداً دوباره تلاش کنید یا از عملیات HTTP مستقیم استفاده کنید.",
        "error_content_policy_blocked": "این درخواست طبق سیاست محتوای بات مسدود است.",
        "error_protected_media_blocked": "دانلود محتوای رسانه‌ای محافظت‌شده پشتیبانی نمی‌شود.",
        "error_route_not_configured": "مسیر خروجی انتخاب‌شده تنظیم نشده است.",
        "error_generic": "درخواست به شکل امن قابل انجام نبود.",
        "error_retryable_hint": " می‌توانید بعداً دوباره تلاش کنید.",
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
