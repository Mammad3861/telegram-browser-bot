from app.config import Settings, parse_telegram_ids
from app.core import access_control


def test_parse_telegram_ids() -> None:
    assert parse_telegram_ids("123, 456,,123") == {123, 456}
    assert parse_telegram_ids("") == set()


def test_admin_is_always_allowed(monkeypatch) -> None:
    settings = Settings(admin_telegram_ids="10", allowed_telegram_ids="")
    monkeypatch.setattr(access_control, "get_settings", lambda: settings)

    assert access_control.is_admin(10)
    assert access_control.is_allowed_user(10)


def test_empty_allowed_list_restricts_access_to_admins(monkeypatch) -> None:
    settings = Settings(admin_telegram_ids="10", allowed_telegram_ids="")
    monkeypatch.setattr(access_control, "get_settings", lambda: settings)

    assert not access_control.is_allowed_user(20)


def test_configured_allowed_user_has_access(monkeypatch) -> None:
    settings = Settings(admin_telegram_ids="10", allowed_telegram_ids="20,30")
    monkeypatch.setattr(access_control, "get_settings", lambda: settings)

    assert access_control.is_allowed_user(20)
    assert not access_control.is_allowed_user(40)
