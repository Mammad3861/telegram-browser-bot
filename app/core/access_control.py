from app.config import get_settings, parse_telegram_ids


def is_admin(user_id: int) -> bool:
    return user_id in parse_telegram_ids(get_settings().admin_telegram_ids)


def is_allowed_user(user_id: int) -> bool:
    settings = get_settings()
    if is_admin(user_id):
        return True
    allowed_ids = parse_telegram_ids(settings.allowed_telegram_ids)
    return bool(allowed_ids) and user_id in allowed_ids
