from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    telegram_bot_token: str = ""
    admin_telegram_ids: str = ""
    allowed_telegram_ids: str = ""
    request_timeout_seconds: float = 10.0
    max_response_bytes: int = 1_000_000
    max_html_size_mb: int = 5
    downloads_dir: str = "downloads"
    min_free_disk_mb: int = 512
    max_download_size_mb: int = 50
    telegram_max_upload_size_mb: int = 50
    max_downloads_per_user_per_day: int = 10
    max_concurrent_jobs_global: int = 3
    max_concurrent_jobs_per_user: int = 1
    browser_timeout_seconds: float = 45.0
    screenshot_viewport_width: int = 1366
    screenshot_viewport_height: int = 768
    max_screenshot_size_mb: int = 20
    max_pdf_size_mb: int = 30
    pdf_format: str = "A4"
    pdf_print_background: bool = True
    rendered_html_wait_until: str = "domcontentloaded"
    cookie_encryption_key: str = ""
    session_storage_dir: str = "downloads/sessions"
    enable_cookie_import: bool = True
    max_cookie_import_size_kb: int = 256
    access_storage_path: str = "downloads/access/allowed_users.json"
    enable_runtime_access_management: bool = True
    cleanup_max_age_hours: int = 24
    delete_generated_files_after_send: bool = True
    url_session_ttl_minutes: int = 60
    register_bot_commands: bool = True
    force_persian_command_menu: bool = False
    command_menu_language_mode: str = "auto"
    reset_telegram_commands_on_start: bool = False
    search_provider: str = "duckduckgo_html"
    search_results_limit: int = 5
    search_timeout_seconds: float = 15.0
    brave_search_api_key: str = ""
    searxng_base_url: str = ""
    search_query_max_length: int = 200
    search_session_ttl_minutes: int = 30
    user_preferences_path: str = "downloads/preferences/user_preferences.json"
    bot_texts_path: str = "downloads/texts/bot_texts.json"
    bot_text_max_length: int = 3000
    url_sessions_path: str = "downloads/ui_sessions/url_sessions.json"
    url_session_max_stored: int = 500
    search_sessions_path: str = "downloads/ui_sessions/search_sessions.json"
    search_session_max_stored: int = 300
    job_history_path: str = "downloads/jobs/job_history.json"
    job_history_max_stored: int = 1000
    content_policy_path: str = "downloads/policies/content_policy.json"
    enable_content_policy: bool = True
    content_policy_default_action: str = "allow"
    routing_profile: str = "default"
    http_proxy_url: str = ""
    https_proxy_url: str = ""
    playwright_proxy_server: str = ""
    domain_route_rules_path: str = "downloads/policies/route_rules.json"
    interaction_max_elements: int = 10
    interaction_timeout_seconds: float = 30.0
    enable_builtin_safety_blocklist: bool = True
    builtin_adult_category_enabled: bool = True
    builtin_gambling_category_enabled: bool = True
    builtin_crypto_category_enabled: bool = True
    builtin_media_category_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def parse_telegram_ids(value: str) -> set[int]:
    ids: set[int] = set()
    for item in value.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            ids.add(int(item))
        except ValueError as exc:
            raise ValueError(f"Invalid Telegram user ID: {item}") from exc
    return ids
