import logging

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from app.config import Settings, parse_telegram_ids


logger = logging.getLogger(__name__)


def build_default_commands(language: str = "en") -> list[BotCommand]:
    descriptions = (
        {
            "start": "شروع ربات",
            "menu": "باز کردن منوی اصلی",
            "help": "نمایش راهنما",
            "language": "تغییر زبان",
            "about": "درباره این ربات",
            "sessions": "مدیریت نشست‌ها",
            "whoami": "نمایش شناسه تلگرام شما",
        }
        if language == "fa"
        else {
            "start": "Start the bot",
            "menu": "Open interactive menu",
            "help": "Show help",
            "language": "Change language",
            "about": "About this bot",
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
            "admin_status": "نمایش وضعیت اجرا",
            "allowed_users": "نمایش کاربران مجاز",
            "allow": "دادن دسترسی به کاربر",
            "deny": "لغو دسترسی کاربر",
            "cleanup": "حذف فایل‌های قدیمی",
        }
        if language == "fa"
        else {
            "admin_status": "Show runtime status",
            "allowed_users": "List allowed users",
            "allow": "Grant runtime access",
            "deny": "Revoke runtime access",
            "cleanup": "Delete old generated files",
        }
    )
    return [
        BotCommand(command=command, description=description)
        for command, description in descriptions.items()
    ]


async def register_bot_commands(bot: Bot, settings: Settings) -> bool:
    if not settings.register_bot_commands:
        logger.info("Telegram bot command registration is disabled")
        return False

    try:
        await bot.set_my_commands(
            build_default_commands("en"), scope=BotCommandScopeDefault()
        )
        await bot.set_my_commands(
            build_default_commands("fa"),
            scope=BotCommandScopeDefault(),
            language_code="fa",
        )
        for admin_id in parse_telegram_ids(settings.admin_telegram_ids):
            await bot.set_my_commands(
                build_default_commands("en") + build_admin_commands("en"),
                scope=BotCommandScopeChat(chat_id=admin_id),
            )
            await bot.set_my_commands(
                build_default_commands("fa") + build_admin_commands("fa"),
                scope=BotCommandScopeChat(chat_id=admin_id),
                language_code="fa",
            )
    except Exception as exc:
        logger.warning(
            "Telegram command registration failed: exception_type=%s",
            type(exc).__name__,
        )
        return False

    logger.info("Telegram bot commands registered")
    return True

