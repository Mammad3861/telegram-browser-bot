import asyncio

from app.bot.commands import (
    build_admin_commands,
    build_default_commands,
    register_bot_commands,
)
from app.config import Settings


class FakeBot:
    def __init__(self, fail: bool = False) -> None:
        self.calls: list[dict] = []
        self.fail = fail

    async def set_my_commands(self, commands, **kwargs) -> None:
        if self.fail:
            raise RuntimeError("simulated Telegram failure")
        self.calls.append({"commands": commands, **kwargs})


def test_default_command_list_builder() -> None:
    commands = build_default_commands("en")

    assert [command.command for command in commands] == [
        "start",
        "menu",
        "search",
        "help",
        "language",
        "about",
        "sessions",
        "whoami",
    ]
    assert commands[1].description == "Open interactive menu"


def test_admin_command_list_builder() -> None:
    commands = build_admin_commands("en")

    assert [command.command for command in commands] == [
        "admin_status",
        "allowed_users",
        "allow",
        "deny",
        "cleanup",
        "texts",
        "set_text",
        "reset_text",
        "preview_text",
    ]


def test_persian_command_descriptions() -> None:
    commands = {command.command: command for command in build_default_commands("fa")}

    assert commands["menu"].description == "باز کردن منوی اصلی"
    assert commands["language"].description == "تغییر زبان"
    assert commands["sessions"].description == "مدیریت نشست‌ها"


def test_command_values_fit_telegram_limits() -> None:
    commands = (
        build_default_commands("en")
        + build_default_commands("fa")
        + build_admin_commands("en")
        + build_admin_commands("fa")
    )

    assert all(1 <= len(command.command) <= 32 for command in commands)
    assert all(1 <= len(command.description) <= 256 for command in commands)


def test_registration_includes_default_localized_and_admin_scopes() -> None:
    bot = FakeBot()
    settings = Settings(
        _env_file=None,
        admin_telegram_ids="123,456",
        register_bot_commands=True,
    )

    result = asyncio.run(register_bot_commands(bot, settings))  # type: ignore[arg-type]

    assert result is True
    assert len(bot.calls) == 6
    assert bot.calls[0].get("language_code") is None
    assert bot.calls[1]["language_code"] == "fa"
    admin_calls = bot.calls[2:]
    assert {call["scope"].chat_id for call in admin_calls} == {123, 456}
    assert all(len(call["commands"]) == 17 for call in admin_calls)


def test_disabled_registration_makes_no_api_calls() -> None:
    bot = FakeBot()
    settings = Settings(_env_file=None, register_bot_commands=False)

    result = asyncio.run(register_bot_commands(bot, settings))  # type: ignore[arg-type]

    assert result is False
    assert bot.calls == []


def test_registration_failure_is_non_fatal() -> None:
    bot = FakeBot(fail=True)
    settings = Settings(_env_file=None, register_bot_commands=True)

    result = asyncio.run(register_bot_commands(bot, settings))  # type: ignore[arg-type]

    assert result is False
