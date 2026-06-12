from pathlib import Path

from app.config import get_settings, parse_telegram_ids
from app.core.access_store import is_runtime_allowed, remove_allowed_user


def is_admin(user_id: int) -> bool:
    return user_id in parse_telegram_ids(get_settings().admin_telegram_ids)


def is_allowed_user(user_id: int) -> bool:
    settings = get_settings()
    if is_admin(user_id):
        return True
    allowed_ids = parse_telegram_ids(settings.allowed_telegram_ids)
    if user_id in allowed_ids:
        return True
    return is_runtime_allowed(Path(settings.access_storage_path), user_id)


def deny_runtime_user(path: Path, telegram_id: int) -> bool:
    if is_admin(telegram_id):
        raise ValueError("Administrators cannot be denied access")
    return remove_allowed_user(path, telegram_id)
