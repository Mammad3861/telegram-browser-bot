import logging

from aiogram import Bot
from aiogram.types import BotCommand, BotCommandScopeChat, BotCommandScopeDefault

from app.config import Settings, parse_telegram_ids


logger = logging.getLogger(__name__)


def build_default_commands(language: str = "en") -> list[BotCommand]:
    descriptions = (
        {
            "start": "شروع بات",
            "menu": "باز کردن منو",
            "help": "راهنما",
            "language": "تغییر زبان",
            "sessions": "مدیریت نشست‌ها",
            "whoami": "نمایش شناسه تلگرام",
        }
        if language == "fa"
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
            "admin_status": "وضعیت اجرای بات",
            "allowed_users": "کاربران مجاز",
            "cleanup": "پاک‌سازی فایل‌های قدیمی",
            "purge_history": "پاک‌سازی تاریخچه کارها",
            "texts": "مدیریت متن‌های بات",
            "policy": "سیاست محتوا",
            "routes": "مسیرهای خروجی",
            "refresh_commands": "تازه‌سازی منوی دستورها",
        }
        if language == "fa"
        else {
            "admin_status": "Show runtime status",
            "allowed_users": "List allowed users",
            "cleanup": "Delete old generated files",
            "purge_history": "Clear completed job history",
            "texts": "List editable bot texts",
            "policy": "Show content policy",
            "routes": "Show outbound routes",
            "refresh_commands": "Refresh command menus",
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
        mode = settings.command_menu_language_mode.lower()
        if settings.force_persian_command_menu and mode == "auto":
            mode = "force_fa"
        if mode not in {"auto", "force_fa", "force_en"}:
            mode = "auto"
        default_language = "fa" if mode == "force_fa" else "en"
        if settings.reset_telegram_commands_on_start:
            await bot.delete_my_commands(scope=BotCommandScopeDefault())
            await bot.delete_my_commands(
                scope=BotCommandScopeDefault(), language_code="fa"
            )
        await bot.set_my_commands(
            build_default_commands(default_language), scope=BotCommandScopeDefault()
        )
        if mode != "force_en":
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
            if mode != "force_en":
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
