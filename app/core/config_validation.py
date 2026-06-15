import logging
from pathlib import Path

from app.config import Settings
from app.search.providers import SEARCH_PROVIDER_REGISTRY


logger = logging.getLogger(__name__)

VALID_DOWNLOAD_MODES = {"safe", "confirm_unknown", "admin_override"}
VALID_COMMAND_MENU_MODES = {"auto", "force_fa", "force_en", "minimal"}
VALID_CONTENT_POLICY_ACTIONS = {"allow", "block", "deny"}


def validate_startup_config(settings: Settings) -> Settings:
    if settings.search_provider.lower() not in SEARCH_PROVIDER_REGISTRY:
        logger.warning("Invalid SEARCH_PROVIDER configured; search disabled safely")
        settings.search_provider = "disabled"

    if settings.download_mode.lower() not in VALID_DOWNLOAD_MODES:
        logger.warning("Invalid DOWNLOAD_MODE configured; using safe mode")
        settings.download_mode = "safe"

    if settings.command_menu_language_mode.lower() not in VALID_COMMAND_MENU_MODES:
        logger.warning("Invalid TELEGRAM_COMMAND_MENU_MODE configured; using minimal mode")
        settings.command_menu_language_mode = "minimal"

    if settings.content_policy_default_action.lower() not in VALID_CONTENT_POLICY_ACTIONS:
        logger.warning("Invalid CONTENT_POLICY_DEFAULT_ACTION configured; using allow")
        settings.content_policy_default_action = "allow"

    return settings


def persistent_directories(settings: Settings) -> list[Path]:
    paths = [
        Path(settings.downloads_dir),
        Path(settings.session_storage_dir),
        Path(settings.access_storage_path).parent,
        Path(settings.user_preferences_path).parent,
        Path(settings.bot_texts_path).parent,
        Path(settings.url_sessions_path).parent,
        Path(settings.search_sessions_path).parent,
        Path(settings.job_history_path).parent,
        Path(settings.content_policy_path).parent,
        Path(settings.domain_route_rules_path).parent,
        Path(settings.browser_tab_state_dir),
    ]
    return list(dict.fromkeys(paths))


def ensure_startup_directories(settings: Settings) -> None:
    for directory in persistent_directories(settings):
        try:
            directory.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            logger.warning(
                "Could not create runtime directory: path=%s exception_type=%s",
                directory,
                type(exc).__name__,
            )
