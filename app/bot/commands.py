import logging

from aiogram import Bot
from aiogram.types import (
    BotCommand,
    BotCommandScopeAllChatAdministrators,
    BotCommandScopeAllPrivateChats,
    BotCommandScopeChat,
    BotCommandScopeDefault,
)

from app.config import Settings, parse_telegram_ids


logger = logging.getLogger(__name__)
COMMAND_LANGUAGES = (None, "fa", "en", "ru")


def build_default_commands(language: str = "en", compact: bool = False) -> list[BotCommand]:
    if language == "fa":
        descriptions = (
            {
                "start": "شروع",
                "menu": "منو",
                "language": "تغییر زبان",
                "help": "راهنما",
            }
            if compact
            else {
                "start": "شروع بات",
                "menu": "باز کردن منو",
                "help": "راهنما",
                "language": "تغییر زبان",
                "sessions": "مدیریت نشست‌ها",
                "whoami": "نمایش شناسه تلگرام",
            }
        )
    else:
        descriptions = (
            {
                "start": "Start",
                "menu": "Menu",
                "language": "Change language",
                "help": "Help",
            }
            if compact
            else {
                "start": "Start the bot",
                "menu": "Open interactive menu",
                "help": "Show help",
                "language": "Change language",
                "sessions": "Manage saved sessions",
                "whoami": "Show your Telegram ID",
            }
        )
    return [
        BotCommand(command=command, description=description)
        for command, description in descriptions.items()
    ]


def build_admin_commands(language: str = "en") -> list[BotCommand]:
    descriptions = (
        {
            "admin_status": "وضعیت اجرا",
            "setup_check": "بررسی راه‌اندازی",
            "allowed_users": "کاربران مجاز",
            "cleanup": "پاک‌سازی فایل‌های قدیمی",
            "purge_history": "پاک‌سازی تاریخچه کارها",
            "texts": "متن‌های قابل ویرایش",
            "policy": "سیاست محتوا",
            "routes": "مسیرهای خروجی",
            "refresh_commands": "به‌روزرسانی منوی دستورها",
            "debug_commands": "بررسی منوی دستورها",
        }
        if language == "fa"
        else {
            "admin_status": "Show runtime status",
            "setup_check": "Check setup readiness",
            "allowed_users": "List allowed users",
            "cleanup": "Delete old generated files",
            "purge_history": "Clear completed job history",
            "texts": "List editable bot texts",
            "policy": "Show content policy",
            "routes": "Show outbound routes",
            "refresh_commands": "Refresh command menus",
            "debug_commands": "Inspect command menus",
        }
    )
    return [
        BotCommand(command=command, description=description)
        for command, description in descriptions.items()
    ]


def default_language_for_mode(mode: str) -> str:
    return "fa" if mode == "force_fa" else "en"


def build_default_commands_for_mode(mode: str, language: str | None = None) -> list[BotCommand]:
    selected = language or default_language_for_mode(mode)
    return build_default_commands(selected, compact=mode == "force_fa")


def build_admin_commands_for_mode(mode: str, language: str | None = None) -> list[BotCommand]:
    selected = language or default_language_for_mode(mode)
    return build_default_commands_for_mode(mode, selected) + build_admin_commands(selected)


def _scope_language_kwargs(scope: object, language: str | None) -> dict[str, object]:
    kwargs: dict[str, object] = {"scope": scope}
    if language:
        kwargs["language_code"] = language
    return kwargs


async def clear_known_command_scopes(bot: Bot, settings: Settings) -> None:
    scopes: list[object] = [
        BotCommandScopeDefault(),
        BotCommandScopeAllPrivateChats(),
        BotCommandScopeAllChatAdministrators(),
    ]
    scopes.extend(
        BotCommandScopeChat(chat_id=admin_id)
        for admin_id in parse_telegram_ids(settings.admin_telegram_ids)
    )
    for scope in scopes:
        for language in COMMAND_LANGUAGES:
            try:
                await bot.delete_my_commands(**_scope_language_kwargs(scope, language))
            except Exception as exc:
                logger.warning(
                    "Telegram command cleanup failed: scope=%s language=%s exception_type=%s",
                    type(scope).__name__,
                    language or "",
                    type(exc).__name__,
                )


async def register_bot_commands(bot: Bot, settings: Settings) -> bool:
    if not settings.register_bot_commands:
        logger.info("Telegram bot command registration is disabled")
        return False

    try:
        mode = settings.command_menu_language_mode.lower()
        if settings.force_persian_command_menu and mode == "auto":
            mode = "force_fa"
        if mode not in {"auto", "force_fa", "force_en", "minimal"}:
            mode = "minimal"

        await clear_known_command_scopes(bot, settings)
        default_language = default_language_for_mode(mode)
        await bot.set_my_commands(
            build_default_commands_for_mode(mode, default_language),
            scope=BotCommandScopeDefault(),
        )
        if mode == "force_fa":
            await bot.set_my_commands(
                build_default_commands_for_mode(mode, "fa"),
                scope=BotCommandScopeDefault(),
                language_code="fa",
            )
        elif mode not in {"force_en", "minimal"}:
            await bot.set_my_commands(
                build_default_commands("fa"),
                scope=BotCommandScopeDefault(),
                language_code="fa",
            )
            await bot.set_my_commands(
                build_default_commands("en"),
                scope=BotCommandScopeDefault(),
                language_code="en",
            )

        for admin_id in parse_telegram_ids(settings.admin_telegram_ids):
            await bot.set_my_commands(
                build_admin_commands_for_mode(mode, default_language),
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
            if mode == "force_fa":
                await bot.set_my_commands(
                    build_admin_commands_for_mode(mode, "fa"),
                    scope=BotCommandScopeChat(chat_id=admin_id),
                    language_code="fa",
                )
            elif mode not in {"force_en", "minimal"}:
                await bot.set_my_commands(
                    build_default_commands("fa") + build_admin_commands("fa"),
                    scope=BotCommandScopeChat(chat_id=admin_id),
                    language_code="fa",
                )
                await bot.set_my_commands(
                    build_default_commands("en") + build_admin_commands("en"),
                    scope=BotCommandScopeChat(chat_id=admin_id),
                    language_code="en",
                )
    except Exception as exc:
        logger.warning(
            "Telegram command registration failed: exception_type=%s",
            type(exc).__name__,
        )
        return False

    logger.info("Telegram bot commands registered")
    return True
