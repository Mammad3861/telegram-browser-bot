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
