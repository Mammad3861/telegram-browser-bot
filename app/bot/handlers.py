import asyncio
import json
import logging
from pathlib import Path
from urllib.parse import urlparse

from aiogram import F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject
from aiogram.types import CallbackQuery, FSInputFile, Message

from app.config import get_settings, parse_telegram_ids
from app.core.access_control import deny_runtime_user, is_admin, is_allowed_user
from app.core.access_store import (
    add_allowed_user,
    list_allowed_users,
)
from app.core.download_quota import download_quota
from app.core.cookies import CookieValidationError, normalize_domain, validate_cookies_json
from app.core.command_args import CommandArgumentError, parse_single_url_arg
from app.core.cleanup import cleanup_generated_files
from app.core.content_policy import (
    POLICY_CATEGORIES,
    ContentPolicy,
    PolicyDecision,
    add_category_domain,
    add_domain_rule,
    apply_builtin_safety_lists,
    check_query_allowed,
    check_url_allowed,
    is_protected_media_domain,
    load_content_policy,
    normalize_domain as normalize_policy_domain,
    remove_category_domain,
    remove_domain_rule,
    update_category_rule,
)
from app.core.bot_text_store import (
    BotTextValidationError,
    EDITABLE_TEXT_KEYS,
    reset_bot_text,
    set_bot_text,
)
from app.core.browser_tab_state import load_tab_storage_state, save_tab_storage_state
from app.core.encryption import EncryptionError
from app.core.job_history import (
    JobHistoryEntry,
    find_job_history,
    list_user_job_history,
    load_job_history,
    purge_job_history,
)
from app.core.jobs import Job, JobLimitError, JobStore, job_store
from app.core.session_store import (
    delete_session,
    list_sessions,
    load_cookies_for_domain,
    save_cookies,
)
from app.core.runtime_status import RUNTIME_TARGET, build_admin_status
from app.core.storage import StorageError
from app.core.routing import (
    RoutingError,
    http_proxy_for_url,
    load_route_rules,
    playwright_proxy_for_route,
    remove_route_rule,
    route_for_url,
    set_route_rule,
)
from app.core.temp_files import cleanup_sent_file
from app.core.url_sessions import (
    URLSessionExpired,
    URLSessionNotFound,
    URLSessionNotOwned,
    url_session_store,
)
from app.core.url_validation import URLValidationError, validate_url
from app.bot.i18n import TEXTS, bot_text, get_language, set_language, text
from app.bot.commands import register_bot_commands
from app.bot.ui import (
    detect_plain_url,
    interaction_keyboard,
    menu_keyboard,
    parse_url_callback_data,
    url_action_keyboard,
)
from app.fetchers.http_fetcher import FetchError, HttpFetcher, safe_response_text
from app.fetchers.browser_screenshot import (
    BrowserNotInstalledError,
    ScreenshotError,
    ScreenshotOptions,
    ScreenshotTimeoutError,
    ScreenshotTooLargeError,
    capture_screenshot,
)
from app.fetchers.browser_pdf import (
    PdfBrowserNotInstalledError,
    PdfError,
    PdfOptions,
    PdfTimeoutError,
    PdfTooLargeError,
    export_pdf,
)
from app.fetchers.browser_html import (
    RenderedHtmlBrowserNotInstalledError,
    RenderedHtmlError,
    RenderedHtmlOptions,
    RenderedHtmlTimeoutError,
    export_rendered_html,
)
from app.fetchers.browser_diagnostics import map_browser_runtime_error
from app.fetchers.file_downloader import DownloadError, FileDownloader
from app.fetchers.file_detector import is_direct_file
from app.fetchers.html_export import save_html
from app.fetchers.link_extractor import LinkExtractor
from app.fetchers.browser_interaction import (
    InteractiveElement,
    activate_interactive_element,
    extract_interactive_elements,
    extract_page_links,
    option_label,
)
from app.version import APP_VERSION
from app.search.providers import (
    SearchConfigurationError,
    SearchDisabledError,
    SearchResult,
    provider_display_name,
    search_web,
)
from app.search.service import (
    SearchQueryError,
    filter_safe_search_results,
    validate_search_query,
)
from app.search.sessions import (
    SearchSessionExpired,
    SearchSessionNotFound,
    SearchSessionNotOwned,
    search_session_store,
)
from app.search.ui import (
    format_search_results,
    parse_search_callback_data,
    search_results_keyboard,
)

router = Router()
logger = logging.getLogger(__name__)

HELP_TEXT = text("help", "en")

pending_cookie_imports: dict[int, str] = {}
pending_user_inputs: dict[int, str] = {}
pending_interactions: dict[tuple[int, str], list[InteractiveElement]] = {}
job_tab_ids: dict[str, str] = {}
POLICY_CATEGORY_NAMES = POLICY_CATEGORIES


def begin_user_input(user_id: int, mode: str) -> None:
    if mode not in {"search", "url"}:
        raise ValueError("Unsupported input mode")
    pending_user_inputs[user_id] = mode


def consume_user_input(user_id: int) -> str | None:
    return pending_user_inputs.pop(user_id, None)


def invalidate_page_options(user_id: int, tab_id: str) -> None:
    pending_interactions.pop((user_id, tab_id), None)


def policy_category_label(category: str, language: str) -> str:
    return text(f"policy_category_{category}", language)


def policy_reason_label(reason: str, language: str) -> str:
    key = f"policy_reason_{reason}"
    return text(key, language) if key in TEXTS["en"] else reason


def route_label(route: str, language: str) -> str:
    key = f"route_{route}"
    return text(key, language) if key in TEXTS["en"] else route


def get_user_id(message: Message) -> int | None:
    return message.from_user.id if message.from_user else None


def current_content_policy() -> ContentPolicy:
    settings = get_settings()
    policy = load_content_policy(
        Path(settings.content_policy_path), settings.content_policy_default_action
    )
    if settings.enable_builtin_safety_blocklist:
        apply_builtin_safety_lists(
            policy,
            settings.builtin_adult_category_enabled,
            settings.builtin_gambling_category_enabled,
            settings.builtin_crypto_category_enabled,
            settings.builtin_media_category_enabled,
        )
    return policy


def policy_decision(url: str) -> PolicyDecision:
    validate_url(url)
    if not get_settings().enable_content_policy:
        return PolicyDecision(True, "policy_disabled")
    return check_url_allowed(url, current_content_policy())


def is_policy_allowed(url: str) -> bool:
    return policy_decision(url).allowed


def route_name_for_url(url: str) -> str:
    settings = get_settings()
    return route_for_url(
        url, Path(settings.domain_route_rules_path), settings.routing_profile
    )


def http_proxy_for_target(url: str) -> str | None:
    settings = get_settings()
    return http_proxy_for_url(
        url,
        route_name_for_url(url),
        settings.http_proxy_url,
        settings.https_proxy_url,
    )


def browser_proxy_for_target(url: str) -> str | None:
    settings = get_settings()
    return playwright_proxy_for_route(
        route_name_for_url(url), settings.playwright_proxy_server
    )


def policy_block_message(language: str) -> str:
    return text("content_policy_blocked", language)


def validate_action_url(url: str, command: str | None = None) -> str:
    validated = validate_url(url)
    decision = policy_decision(validated)
    if not decision.allowed:
        raise PermissionError("content_policy_blocked")
    hostname = urlparse(validated).hostname or ""
    if (
        command == "download"
        and is_protected_media_domain(hostname)
        and not is_direct_file(validated)
    ):
        raise PermissionError("protected_media_download")
    return validated


def permission_error_message(error: PermissionError, language: str) -> str:
    return text(
        "protected_media_download"
        if str(error) == "protected_media_download"
        else "content_policy_blocked",
        language,
    )


async def reject_unless_allowed(message: Message) -> bool:
    user_id = get_user_id(message)
    if user_id is None or not is_allowed_user(user_id):
        await message.answer(text("access_denied", get_language(user_id)))
        return True
    return False


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    language = get_language(get_user_id(message))
    await message.answer(
        bot_text("welcome", language), reply_markup=menu_keyboard(language)
    )


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    language = get_language(get_user_id(message))
    await message.answer(
        bot_text("help", language), reply_markup=menu_keyboard(language)
    )


@router.message(Command("menu"))
async def menu_handler(message: Message) -> None:
    language = get_language(get_user_id(message))
    await message.answer(text("menu", language), reply_markup=menu_keyboard(language))


@router.message(Command("about"))
async def about_handler(message: Message) -> None:
    language = get_language(get_user_id(message))
    await message.answer(
        bot_text(
            "about",
            language,
            version=APP_VERSION,
            runtime_target=RUNTIME_TARGET,
        )
    )


@router.message(Command("language"))
async def language_handler(message: Message, command: CommandObject) -> None:
    user_id = get_user_id(message)
    language = get_language(user_id)
    if not command.args:
        await message.answer(text("language_current", language, language=language))
        return
    if user_id is None:
        await message.answer(text("language_usage", language))
        return
    try:
        selected = set_language(user_id, command.args)
    except ValueError:
        await message.answer(text("language_usage", language))
        return
    await message.answer(
        text("language_updated", selected, language=selected),
        reply_markup=menu_keyboard(selected),
    )


@router.callback_query(F.data.startswith("menu:"))
async def menu_callback_handler(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    language = get_language(user_id)
    action = (callback.data or "").partition(":")[2]
    await callback.answer()
    if callback.message is None:
        return
    if action == "open_url":
        begin_user_input(user_id, "url")
        await callback.message.answer(text("url_input_prompt", language))
    elif action == "sessions":
        if not is_allowed_user(user_id):
            await callback.message.answer(text("access_denied", language))
            return
        sessions = list_sessions(user_id)
        await callback.message.answer(
            text("sessions_list", language, sessions="\n".join(sessions))
            if sessions
            else text("sessions", language)
        )
    elif action == "jobs":
        jobs = list_job_records(
            user_id,
            is_admin(user_id),
            job_store,
            Path(get_settings().job_history_path),
        )
        await callback.message.answer(
            "\n\n".join(
                format_job(job, language)
                if isinstance(job, Job)
                else format_job_history(job, language)
                for job in jobs[:5]
            )
            if jobs
            else text("no_jobs", language)
        )
    elif action == "help":
        await callback.message.answer(
            bot_text("help", language), reply_markup=menu_keyboard(language)
        )
    elif action == "search":
        if not is_allowed_user(user_id):
            await callback.message.answer(text("access_denied", language))
            return
        begin_user_input(user_id, "search")
        await callback.message.answer(text("search_input_prompt", language))
    elif action == "language":
        await callback.message.answer(text("language_current", language, language=language))


async def perform_search(query: str) -> list[SearchResult]:
    settings = get_settings()
    policy = current_content_policy()
    if settings.enable_content_policy and policy.enabled and not check_query_allowed(
        query, policy
    ).allowed:
        raise PermissionError("content_policy_blocked")
    limit = max(1, min(settings.search_results_limit, 5))
    results = await search_web(
        settings.search_provider,
        query,
        limit,
        settings.search_timeout_seconds,
        settings.brave_search_api_key,
        settings.searxng_base_url,
    )
    safe_results = filter_safe_search_results(results, limit)
    return [result for result in safe_results if is_policy_allowed(result.url)][:limit]


async def send_search_results(
    message: Message, user_id: int, query: str, language: str
) -> None:
    results = await perform_search(query)
    if not results:
        await message.answer(text("search_no_results", language))
        return
    session = search_session_store.create(user_id, query, results)
    settings = get_settings()
    requested = max(1, min(settings.search_results_limit, 5))
    provider = provider_display_name(results[0].source if results else settings.search_provider)
    await message.answer(
        format_search_results(
            query,
            results,
            text("search_results", language, query=query),
            text("search_source", language, provider=provider),
            (
                text(
                    "search_partial_results",
                    language,
                    count=len(results),
                    requested=requested,
                )
                if len(results) < requested
                else None
            ),
        ),
        reply_markup=search_results_keyboard(
            session.session_id, len(results), language
        ),
    )


@router.message(Command("search"))
async def search_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    user_id = get_user_id(message)
    language = get_language(user_id)
    if user_id is None:
        await message.answer(text("search_unavailable", language))
        return
    settings = get_settings()
    try:
        query = validate_search_query(command.args, settings.search_query_max_length)
    except SearchQueryError:
        if command.args and command.args.strip():
            await message.answer(
                text(
                    "search_query_too_long",
                    language,
                    max_length=settings.search_query_max_length,
                )
            )
        else:
            await message.answer(text("search_usage", language))
        return
    try:
        await send_search_results(message, user_id, query, language)
    except SearchDisabledError:
        await message.answer(text("search_disabled", language))
    except SearchConfigurationError:
        logger.warning("Search provider is misconfigured")
        await message.answer(text("search_misconfigured", language))
    except PermissionError as exc:
        await message.answer(permission_error_message(exc, language))
    except Exception as exc:
        logger.warning("Search failed: exception_type=%s", type(exc).__name__)
        await message.answer(text("search_unavailable", language))


@router.callback_query(F.data.startswith("search:"))
async def search_callback_handler(callback: CallbackQuery) -> None:
    parsed = parse_search_callback_data(callback.data)
    if parsed is None:
        await callback.answer(
            text("invalid_action", get_language(callback.from_user.id)), show_alert=True
        )
        return
    user_id = callback.from_user.id
    language = get_language(user_id)
    if not is_allowed_user(user_id):
        await callback.answer(text("access_denied", language), show_alert=True)
        return
    try:
        session = search_session_store.get_for_user(
            parsed.session_id,
            user_id,
            get_settings().search_session_ttl_minutes,
        )
    except (SearchSessionNotFound, SearchSessionExpired):
        await callback.answer(text("search_expired", language), show_alert=True)
        return
    except SearchSessionNotOwned:
        await callback.answer(text("search_not_owned", language), show_alert=True)
        return

    message = callback.message
    if message is None:
        await callback.answer()
        return
    if parsed.action == "close":
        search_session_store.cancel(session.session_id, user_id)
        await callback.answer()
        await message.edit_text(text("search_closed", language))
        return
    if parsed.action == "open":
        if parsed.index is None or parsed.index >= len(session.results):
            await callback.answer(text("search_expired", language), show_alert=True)
            return
        result = session.results[parsed.index]
        try:
            url = validate_action_url(result.url)
        except URLValidationError:
            await callback.answer(text("invalid_url", language), show_alert=True)
            return
        except PermissionError as exc:
            await callback.answer(permission_error_message(exc, language), show_alert=True)
            return
        await callback.answer(text("search_opening", language))
        await create_url_card(message, user_id, url)
        return

    await callback.answer()
    try:
        results = await perform_search(session.query)
        if not results:
            await message.answer(text("search_no_results", language))
            return
        updated = search_session_store.update_results(session.session_id, results)
        if updated is None:
            await message.answer(text("search_expired", language))
            return
        await message.edit_text(
            format_search_results(
                updated.query,
                updated.results,
                text("search_results", language, query=updated.query),
                text(
                    "search_source",
                    language,
                    provider=provider_display_name(updated.results[0].source),
                ),
                (
                    text(
                        "search_partial_results",
                        language,
                        count=len(updated.results),
                        requested=max(
                            1, min(get_settings().search_results_limit, 5)
                        ),
                    )
                    if len(updated.results)
                    < max(1, min(get_settings().search_results_limit, 5))
                    else None
                ),
            ),
            reply_markup=search_results_keyboard(
                updated.session_id, len(updated.results), language
            ),
        )
    except SearchDisabledError:
        await message.answer(text("search_disabled", language))
    except SearchConfigurationError:
        logger.warning("Search provider is misconfigured during refresh")
        await message.answer(text("search_misconfigured", language))
    except Exception as exc:
        logger.warning("Search refresh failed: exception_type=%s", type(exc).__name__)
        await message.answer(text("search_unavailable", language))


async def create_url_card(message: Message, user_id: int, url: str) -> None:
    language = get_language(user_id)
    try:
        url = validate_action_url(url)
    except PermissionError as exc:
        await message.answer(permission_error_message(exc, language))
        return
    session = url_session_store.create(user_id, url)
    hostname = urlparse(url).hostname or ""
    card_text = text("url_card", language, url=url, title=hostname or url)
    if is_protected_media_domain(hostname):
        card_text += "\n\n" + text("media_site_note", language)
    sent = await message.answer(
        card_text,
        reply_markup=url_action_keyboard(session.session_id, language),
    )
    url_session_store.touch(session.session_id, sent.message_id)


@router.callback_query(F.data.startswith("url:"))
async def url_action_callback_handler(callback: CallbackQuery) -> None:
    parsed = parse_url_callback_data(callback.data)
    if parsed is None:
        await callback.answer(
            text("invalid_action", get_language(callback.from_user.id)), show_alert=True
        )
        return
    user_id = callback.from_user.id
    language = get_language(user_id)
    if not is_allowed_user(user_id):
        await callback.answer(text("access_denied", language), show_alert=True)
        return
    try:
        session = url_session_store.get_for_user(
            parsed.session_id,
            user_id,
            get_settings().url_session_ttl_minutes,
        )
        validate_action_url(session.url, parsed.action)
    except (URLSessionNotFound, URLSessionExpired):
        await callback.answer(text("session_expired", language), show_alert=True)
        return
    except URLSessionNotOwned:
        await callback.answer(text("session_not_owned", language), show_alert=True)
        return
    except URLValidationError:
        await callback.answer(text("invalid_url", language), show_alert=True)
        return
    except PermissionError as exc:
        await callback.answer(permission_error_message(exc, language), show_alert=True)
        return

    await callback.answer()
    message = callback.message
    if message is None:
        return
    if parsed.action == "cancel":
        url_session_store.cancel(session.session_id, user_id)
        await message.edit_text(text("url_cancelled", language))
        return
    if parsed.action == "refresh":
        url_session_store.touch(session.session_id, message.message_id)
        await message.edit_text(
            text(
                "url_refreshed",
                language,
                title=session.title or urlparse(session.url).hostname or session.url,
                url=session.url,
            )
            + (
                "\n\n" + text("media_site_note", language)
                if is_protected_media_domain(urlparse(session.url).hostname or "")
                else ""
            ),
            reply_markup=url_action_keyboard(session.session_id, language),
        )
        return
    if parsed.action == "back":
        previous = url_session_store.back(session.session_id, user_id)
        if previous is None:
            await message.answer(text("tab_back_unavailable", language))
            return
        await message.edit_text(
            text(
                "url_refreshed",
                language,
                title=previous.title or urlparse(previous.url).hostname or previous.url,
                url=previous.url,
            ),
            reply_markup=url_action_keyboard(previous.session_id, language),
        )
        return
    if parsed.action == "interact":
        settings = get_settings()
        try:
            elements = await extract_interactive_elements(
                session.url,
                settings.interaction_timeout_seconds,
                settings.interaction_max_elements,
                browser_cookies_for_user_url(user_id, session.url),
                browser_proxy_for_target(session.url),
                browser_storage_for_tab(user_id, session.session_id),
            )
        except Exception as exc:
            logger.warning("Interaction extraction failed: exception_type=%s", type(exc).__name__)
            await message.answer(text("interaction_failed", language))
            return
        if not elements:
            await message.answer(text("interaction_none", language))
            return
        pending_interactions[(user_id, session.session_id)] = elements
        await message.answer(
            text("interaction_choose", language),
            reply_markup=interaction_keyboard(
                session.session_id,
                [option_label(element, session.url) for element in elements],
            ),
        )
        return
    if parsed.action == "links":
        try:
            links = await extract_page_links(
                session.url,
                get_settings().interaction_timeout_seconds,
                browser_cookies_for_user_url(user_id, session.url),
                browser_proxy_for_target(session.url),
                browser_storage_for_tab(user_id, session.session_id),
            )
            await message.answer(
                "\n".join(links[:50])[:4000] if links else text("no_links", language)
            )
        except RoutingError:
            await message.answer(text("proxy_not_configured", language))
        except Exception as exc:
            logger.warning("Tab link extraction failed: exception_type=%s", type(exc).__name__)
            await message.answer(text("browser_request_failed", language))
        return

    command = "html_rendered" if parsed.action == "rendered_html" else parsed.action
    settings = get_settings()
    if command == "download":
        if download_quota.remaining(
            user_id, settings.max_downloads_per_user_per_day
        ) <= 0:
            await message.answer(text("daily_quota_exceeded", language))
            return
    try:
        if command in {"html_rendered", "screenshot", "pdf"}:
            browser_proxy_for_target(session.url)
        else:
            http_proxy_for_target(session.url)
        job = create_background_job_for_user(user_id, command, session.url)
        if command in {"html_rendered", "screenshot", "pdf"}:
            job_tab_ids[job.id] = session.session_id
        if command == "download":
            download_quota.consume(user_id, settings.max_downloads_per_user_per_day)
        await message.answer(
            text(
                "job_started",
                language,
                job_id=job.id,
                status=job_status_text(job.status, language),
            )
        )
        runner = {
            "html": run_html_job,
            "html_rendered": run_rendered_html_job,
            "download": run_download_job,
            "screenshot": run_screenshot_job,
            "pdf": run_pdf_job,
        }[command]
        task = asyncio.create_task(runner(job, message))
        job_store.register_task(job.id, task)
    except JobLimitError as exc:
        await message.answer(text("request_failed", language, error=str(exc)))
    except RoutingError:
        await message.answer(text("proxy_not_configured", language))


@router.message(Command("whoami"))
async def whoami_handler(message: Message) -> None:
    user_id = get_user_id(message)
    language = get_language(user_id)
    await message.answer(
        text("whoami", language, user_id=user_id)
        if user_id is not None
        else text("user_id_unavailable", language)
    )


@router.message(Command("access"))
async def access_handler(message: Message) -> None:
    user_id = get_user_id(message)
    if user_id is None or not is_admin(user_id):
        await message.answer(text("admin_required", get_language(user_id)))
        return
    language = get_language(user_id)
    settings = get_settings()
    static_allowed = parse_telegram_ids(settings.allowed_telegram_ids)
    runtime_allowed = list_allowed_users(Path(settings.access_storage_path))
    await message.answer(text(
        "access_status",
        language,
        user_id=user_id,
        admin=text("yes", language),
        runtime_state=text(
            "enabled" if settings.enable_runtime_access_management else "disabled",
            language,
        ),
        static_count=len(static_allowed),
        runtime_count=len(runtime_allowed),
    ))


def parse_access_target(arguments: str | None) -> tuple[int, str | None]:
    if not arguments:
        raise ValueError("Telegram ID is required")
    parts = arguments.strip().split(maxsplit=1)
    try:
        telegram_id = int(parts[0])
    except ValueError as exc:
        raise ValueError("Telegram ID must be an integer") from exc
    note = parts[1].strip() if len(parts) > 1 and parts[1].strip() else None
    return telegram_id, note


def runtime_access_path() -> Path:
    return Path(get_settings().access_storage_path)


async def require_runtime_admin(message: Message) -> int | None:
    user_id = get_user_id(message)
    language = get_language(user_id)
    if user_id is None or not is_admin(user_id):
        await message.answer(text("admin_required", language))
        return None
    if not get_settings().enable_runtime_access_management:
        await message.answer(text("runtime_access_disabled", language))
        return None
    return user_id


async def require_admin(message: Message) -> int | None:
    user_id = get_user_id(message)
    if user_id is None or not is_admin(user_id):
        await message.answer(text("admin_required", get_language(user_id)))
        return None
    return user_id


@router.message(Command("allow"))
async def allow_handler(message: Message, command: CommandObject) -> None:
    admin_id = await require_runtime_admin(message)
    if admin_id is None:
        return
    try:
        telegram_id, note = parse_access_target(command.args)
    except ValueError as exc:
        key = "access_target_invalid" if "integer" in str(exc) else "access_target_required"
        await message.answer(text(key, get_language(admin_id)))
        return
    added = add_allowed_user(runtime_access_path(), telegram_id, admin_id, note)
    await message.answer(text(
        "access_granted" if added else "access_already_allowed",
        get_language(admin_id),
        user_id=telegram_id,
    ))


@router.message(Command("deny"))
async def deny_handler(message: Message, command: CommandObject) -> None:
    admin_id = await require_runtime_admin(message)
    if admin_id is None:
        return
    try:
        telegram_id, _ = parse_access_target(command.args)
    except ValueError as exc:
        key = "access_target_invalid" if "integer" in str(exc) else "access_target_required"
        await message.answer(text(key, get_language(admin_id)))
        return
    try:
        removed = deny_runtime_user(runtime_access_path(), telegram_id)
    except ValueError:
        await message.answer(text("admin_cannot_be_denied", get_language(admin_id)))
        return
    await message.answer(text(
        "access_revoked" if removed else "access_user_not_found",
        get_language(admin_id),
        user_id=telegram_id,
    ))


@router.message(Command("allowed_users"))
async def allowed_users_handler(message: Message) -> None:
    admin_id = await require_runtime_admin(message)
    if admin_id is None:
        return
    language = get_language(admin_id)
    settings = get_settings()
    static_ids = sorted(parse_telegram_ids(settings.allowed_telegram_ids))
    runtime_users = list_allowed_users(runtime_access_path())
    static_text = ", ".join(map(str, static_ids)) if static_ids else text("none", language)
    runtime_text = "\n".join(
        f"{user.telegram_id}"
        + (f" - {user.note}" if user.note else "")
        for user in runtime_users
    ) or text("none", language)
    await message.answer(text(
        "allowed_users_list",
        language,
        static_users=static_text,
        runtime_users=runtime_text,
    ))


def parse_set_text_args(arguments: str | None) -> tuple[str, str, str]:
    if not arguments:
        raise BotTextValidationError(
            "Usage: /set_text <key> <lang> <text>", "set_text_usage"
        )
    parts = arguments.strip().split(maxsplit=2)
    if len(parts) != 3:
        raise BotTextValidationError(
            "Usage: /set_text <key> <lang> <text>", "set_text_usage"
        )
    return parts[0], parts[1], parts[2]


def parse_text_target_args(
    arguments: str | None, default_language: str | None = None
) -> tuple[str, str | None]:
    if not arguments:
        raise BotTextValidationError("Text key is required", "text_key_required")
    parts = arguments.strip().split(maxsplit=1)
    return parts[0], parts[1] if len(parts) == 2 else default_language


@router.message(Command("texts"))
async def texts_handler(message: Message) -> None:
    admin_id = await require_admin(message)
    if admin_id is None:
        return
    await message.answer(text("texts_overview", get_language(admin_id)))


def localized_bot_text_error(
    error: BotTextValidationError, language: str, max_length: int
) -> str:
    key_by_code = {
        "invalid_key": "text_invalid_key",
        "invalid_language": "text_invalid_language",
        "text_too_long": "text_too_long",
        "empty_text": "text_empty",
        "text_key_required": "text_key_required",
        "set_text_usage": "set_text_usage",
    }
    key = key_by_code.get(error.code, "set_text_usage")
    return text(key, language, max_length=max_length)


@router.message(Command("set_text"))
async def set_text_handler(message: Message, command: CommandObject) -> None:
    admin_id = await require_admin(message)
    if admin_id is None:
        return
    settings = get_settings()
    locale = get_language(admin_id)
    try:
        key, language, value = parse_set_text_args(command.args)
        set_bot_text(
            Path(settings.bot_texts_path),
            key,
            language,
            value,
            settings.bot_text_max_length,
        )
    except BotTextValidationError as exc:
        await message.answer(
            localized_bot_text_error(exc, locale, settings.bot_text_max_length)
        )
        return
    await message.answer(
        text("text_updated", locale, key=key, language=language)
    )


@router.message(Command("reset_text"))
async def reset_text_handler(message: Message, command: CommandObject) -> None:
    admin_id = await require_admin(message)
    if admin_id is None:
        return
    settings = get_settings()
    locale = get_language(admin_id)
    try:
        key, language = parse_text_target_args(command.args)
        changed = reset_bot_text(Path(settings.bot_texts_path), key, language)
    except BotTextValidationError as exc:
        await message.answer(
            localized_bot_text_error(exc, locale, settings.bot_text_max_length)
        )
        return
    target = f"{key}/{language}" if language else key
    await message.answer(
        text("text_reset", locale, target=target)
        if changed
        else text("text_override_missing", locale, target=target)
    )


@router.message(Command("preview_text"))
async def preview_text_handler(message: Message, command: CommandObject) -> None:
    admin_id = await require_admin(message)
    if admin_id is None:
        return
    settings = get_settings()
    locale = get_language(admin_id)
    try:
        key, language = parse_text_target_args(
            command.args, default_language=locale
        )
        if key not in EDITABLE_TEXT_KEYS:
            raise BotTextValidationError("Invalid text key", "invalid_key")
        if language not in {"en", "fa"}:
            raise BotTextValidationError("Invalid language", "invalid_language")
        preview = bot_text(
            key,
            language,
            version=APP_VERSION,
            runtime_target=RUNTIME_TARGET,
        )
    except BotTextValidationError as exc:
        await message.answer(
            localized_bot_text_error(exc, locale, settings.bot_text_max_length)
        )
        return
    await message.answer(
        text(
            "text_preview",
            locale,
            key=key,
            language=language,
            preview=preview,
        )
    )


@router.message(Command("admin_status"))
async def admin_status_handler(message: Message) -> None:
    user_id = get_user_id(message)
    if user_id is None or not is_admin(user_id):
        await message.answer(text("admin_required", get_language(user_id)))
        return
    language = get_language(user_id)
    status = build_admin_status(get_settings(), job_store)
    directories = ", ".join(
        f"{name}={text('ready' if exists else 'missing', language)}"
        for name, exists in status.generated_directories.items()
    )
    await message.answer(text(
        "admin_status",
        language,
        version=status.version,
        runtime_target=status.runtime_target,
        active_jobs=status.active_jobs,
        known_jobs=status.known_jobs,
        runtime_users=status.runtime_allowed_users,
        free_bytes=status.storage_free_bytes,
        cookie_state=text("enabled" if status.cookie_import_enabled else "disabled", language),
        directories=directories,
    ))


@router.message(Command("cleanup"))
async def cleanup_handler(message: Message) -> None:
    user_id = get_user_id(message)
    if user_id is None or not is_admin(user_id):
        await message.answer(text("admin_required", get_language(user_id)))
        return
    language = get_language(user_id)
    settings = get_settings()
    try:
        result = cleanup_generated_files(
            Path(settings.downloads_dir), settings.cleanup_max_age_hours
        )
    except OSError:
        await message.answer(text("cleanup_failed", language))
        return
    await message.answer(text(
        "cleanup_summary",
        language,
        count=result.deleted_files,
        bytes=result.freed_bytes,
    ))


@router.message(Command("purge_history"))
async def purge_history_handler(message: Message) -> None:
    user_id = get_user_id(message)
    if user_id is None or not is_admin(user_id):
        await message.answer(text("admin_required", get_language(user_id)))
        return
    language = get_language(user_id)
    try:
        purged = purge_job_history(Path(get_settings().job_history_path))
    except OSError:
        await message.answer(text("purge_history_failed", language))
        return
    await message.answer(text("purge_history_summary", language, count=purged))


@router.message(Command("refresh_commands"))
async def refresh_commands_handler(message: Message) -> None:
    admin_id = await require_admin(message)
    if admin_id is None:
        return
    success = await register_bot_commands(message.bot, get_settings())
    await message.answer(
        text(
            "commands_refresh_success" if success else "commands_refresh_failed",
            get_language(admin_id),
        )
    )


def content_policy_path() -> Path:
    return Path(get_settings().content_policy_path)


@router.message(Command("policy"))
async def policy_handler(message: Message) -> None:
    admin_id = await require_admin(message)
    if admin_id is None:
        return
    language = get_language(admin_id)
    settings = get_settings()
    policy = current_content_policy()
    await message.answer(text(
        "policy_status",
        language,
        state=text(
            "enabled" if settings.enable_content_policy and policy.enabled else "disabled",
            language,
        ),
        default_action=text(
            "allowed"
            if policy.default_action == "allow"
            else "blocked",
            language,
        ),
        blocked=len(policy.blocked_domains),
        allowed=len(policy.allowed_domains),
        categories=", ".join(
            policy_category_label(category, language)
            for category in policy.blocked_categories
        ) or text("none", language),
        allowed_categories=", ".join(
            policy_category_label(category, language)
            for category in policy.allowed_categories
        ) or text("none", language),
        configurable_categories=", ".join(
            policy_category_label(category, language)
            for category in POLICY_CATEGORIES
        ),
        builtin_state=text(
            "enabled" if settings.enable_builtin_safety_blocklist else "disabled",
            language,
        ),
        updated_at=policy.updated_at,
    ))


def category_state(policy: ContentPolicy, category: str) -> str:
    if category in policy.allowed_categories:
        return "allowed"
    if category in policy.blocked_categories:
        return "blocked"
    return "neutral"


def parse_policy_category(raw: str | None) -> str:
    category = (raw or "").strip().lower()
    if category not in POLICY_CATEGORIES:
        raise ValueError("Invalid category")
    return category


@router.message(Command("categories"))
async def categories_handler(message: Message) -> None:
    admin_id = await require_admin(message)
    if admin_id is None:
        return
    language = get_language(admin_id)
    policy = current_content_policy()
    lines = [
        text(
            "policy_category_line",
            language,
            category=policy_category_label(category, language),
            state=text(f"policy_state_{category_state(policy, category)}", language),
        )
        for category in POLICY_CATEGORIES
    ]
    await message.answer(text("policy_categories_title", language, categories="\n".join(lines)))


async def update_category_handler(
    message: Message, command: CommandObject, allow: bool, remove: bool
) -> None:
    admin_id = await require_admin(message)
    if admin_id is None:
        return
    language = get_language(admin_id)
    try:
        category = parse_policy_category(command.args)
    except ValueError:
        await message.answer(text(
            "policy_invalid_category",
            language,
            categories=", ".join(POLICY_CATEGORIES),
        ))
        return
    changed = update_category_rule(content_policy_path(), category, allow, remove)
    current_state = category_state(load_content_policy(content_policy_path()), category)
    await message.answer(text(
        "policy_category_rule_updated" if changed else "policy_category_rule_unchanged",
        language,
        category=policy_category_label(category, language),
        state=text(f"policy_state_{current_state}", language),
    ))


@router.message(Command("block_category"))
async def block_category_handler(message: Message, command: CommandObject) -> None:
    await update_category_handler(message, command, allow=False, remove=False)


@router.message(Command("allow_category"))
async def allow_category_handler(message: Message, command: CommandObject) -> None:
    await update_category_handler(message, command, allow=True, remove=False)


@router.message(Command("unblock_category"))
async def unblock_category_handler(message: Message, command: CommandObject) -> None:
    await update_category_handler(message, command, allow=False, remove=True)


@router.message(Command("unallow_category"))
async def unallow_category_handler(message: Message, command: CommandObject) -> None:
    await update_category_handler(message, command, allow=True, remove=True)


@router.message(Command("category_domains"))
async def category_domains_handler(message: Message, command: CommandObject) -> None:
    admin_id = await require_admin(message)
    if admin_id is None:
        return
    language = get_language(admin_id)
    try:
        category = parse_policy_category(command.args)
    except ValueError:
        await message.answer(text("policy_category_usage", language, command="category_domains"))
        return
    domains = current_content_policy().category_domains.get(category, [])
    await message.answer(text(
        "policy_category_domains",
        language,
        category=policy_category_label(category, language),
        domains="\n".join(domains) or text("none", language),
    ))


async def mutate_category_domain_handler(
    message: Message, command: CommandObject, remove: bool
) -> None:
    admin_id = await require_admin(message)
    if admin_id is None:
        return
    language = get_language(admin_id)
    arguments = (command.args or "").split()
    command_name = "remove_category_domain" if remove else "add_category_domain"
    if len(arguments) != 2:
        await message.answer(text("policy_category_domain_usage", language, command=command_name))
        return
    try:
        category = parse_policy_category(arguments[0])
        domain = normalize_policy_domain(arguments[1])
        changed = (
            remove_category_domain(content_policy_path(), category, domain)
            if remove
            else add_category_domain(content_policy_path(), category, domain)
        )
    except ValueError:
        await message.answer(text(
            "policy_invalid_category_or_domain",
            language,
            categories=", ".join(POLICY_CATEGORIES),
        ))
        return
    await message.answer(text(
        "policy_category_domain_removed" if remove and changed else
        "policy_category_domain_missing" if remove else
        "policy_category_domain_added" if changed else
        "policy_category_domain_exists",
        language,
        category=policy_category_label(category, language),
        domain=domain,
    ))


@router.message(Command("add_category_domain"))
async def add_category_domain_handler(message: Message, command: CommandObject) -> None:
    await mutate_category_domain_handler(message, command, remove=False)


@router.message(Command("remove_category_domain"))
async def remove_category_domain_handler(message: Message, command: CommandObject) -> None:
    await mutate_category_domain_handler(message, command, remove=True)


async def update_policy_domain(
    message: Message, command: CommandObject, allow: bool, remove: bool
) -> None:
    admin_id = await require_admin(message)
    if admin_id is None:
        return
    language = get_language(admin_id)
    arguments = (command.args or "").split()
    command_name = (
        "unallow_domain" if allow and remove else
        "allow_domain" if allow else
        "unblock_domain" if remove else "block_domain"
    )
    if not arguments:
        key = "policy_usage_block" if not allow and not remove else "policy_usage_domain"
        await message.answer(text(key, language, command=command_name))
        return
    category = arguments[1].lower() if len(arguments) > 1 and not allow and not remove else None
    if category and category not in POLICY_CATEGORIES:
        await message.answer(text(
            "policy_invalid_category",
            language,
            categories=", ".join(POLICY_CATEGORY_NAMES),
        ))
        return
    try:
        domain = normalize_policy_domain(arguments[0])
        changed = (
            remove_domain_rule(content_policy_path(), domain, allow)
            if remove
            else add_domain_rule(content_policy_path(), domain, allow, category)
        )
    except ValueError as exc:
        await message.answer(text("request_failed", language, error=str(exc)))
        return
    await message.answer(text(
        "policy_domain_removed" if remove and changed else
        "policy_domain_missing" if remove else
        "policy_domain_added" if changed else "policy_domain_exists",
        language,
        domain=domain,
    ))


@router.message(Command("block_domain"))
async def block_domain_handler(message: Message, command: CommandObject) -> None:
    await update_policy_domain(message, command, allow=False, remove=False)


@router.message(Command("allow_domain"))
async def allow_domain_handler(message: Message, command: CommandObject) -> None:
    await update_policy_domain(message, command, allow=True, remove=False)


@router.message(Command("unblock_domain"))
async def unblock_domain_handler(message: Message, command: CommandObject) -> None:
    await update_policy_domain(message, command, allow=False, remove=True)


@router.message(Command("unallow_domain"))
async def unallow_domain_handler(message: Message, command: CommandObject) -> None:
    await update_policy_domain(message, command, allow=True, remove=True)


@router.message(Command("policy_test"))
async def policy_test_handler(message: Message, command: CommandObject) -> None:
    admin_id = await require_admin(message)
    if admin_id is None:
        return
    language = get_language(admin_id)
    if not command.args:
        await message.answer(text("policy_usage_test", language))
        return
    try:
        decision = policy_decision(parse_single_url_arg(command.args))
    except (CommandArgumentError, URLValidationError, ValueError) as exc:
        await message.answer(text("request_failed", language, error=str(exc)))
        return
    await message.answer(text(
        "policy_test_result",
        language,
        decision=text("allowed" if decision.allowed else "blocked", language),
        reason=policy_reason_label(decision.reason, language),
        category=(
            policy_category_label(decision.category, language)
            if decision.category
            else text("none", language)
        ),
    ))


@router.message(Command("policy_reload"))
async def policy_reload_handler(message: Message) -> None:
    admin_id = await require_admin(message)
    if admin_id is None:
        return
    policy = current_content_policy()
    await message.answer(text(
        "policy_reloaded", get_language(admin_id), count=len(policy.blocked_domains)
    ))


@router.message(Command("routes"))
async def routes_handler(message: Message) -> None:
    admin_id = await require_admin(message)
    if admin_id is None:
        return
    language = get_language(admin_id)
    settings = get_settings()
    rules = load_route_rules(Path(settings.domain_route_rules_path))
    rendered = "\n".join(
        f"{rule.domain}: {route_label(rule.route, language)}" for rule in rules
    )
    await message.answer(text(
        "routes_status",
        language,
        profile=route_label(settings.routing_profile, language),
        rules=rendered or text("route_no_rules", language),
    ))


@router.message(Command("route_domain"))
async def route_domain_handler(message: Message, command: CommandObject) -> None:
    admin_id = await require_admin(message)
    if admin_id is None:
        return
    language = get_language(admin_id)
    parts = (command.args or "").split()
    if len(parts) != 2:
        await message.answer(text("route_usage", language))
        return
    try:
        domain = normalize_policy_domain(parts[0])
        set_route_rule(Path(get_settings().domain_route_rules_path), domain, parts[1])
    except ValueError as exc:
        await message.answer(text("request_failed", language, error=str(exc)))
        return
    await message.answer(text(
        "route_rule_set", language, domain=domain, route=route_label(parts[1], language)
    ))


@router.message(Command("unroute_domain"))
async def unroute_domain_handler(message: Message, command: CommandObject) -> None:
    admin_id = await require_admin(message)
    if admin_id is None:
        return
    language = get_language(admin_id)
    if not command.args:
        await message.answer(text("unroute_usage", language))
        return
    try:
        domain = normalize_policy_domain(command.args)
        changed = remove_route_rule(Path(get_settings().domain_route_rules_path), domain)
    except ValueError as exc:
        await message.answer(text("request_failed", language, error=str(exc)))
        return
    await message.answer(text(
        "route_rule_removed" if changed else "route_rule_missing", language, domain=domain
    ))


@router.message(Command("route_test"))
async def route_test_handler(message: Message, command: CommandObject) -> None:
    admin_id = await require_admin(message)
    if admin_id is None:
        return
    language = get_language(admin_id)
    if not command.args:
        await message.answer(text("route_test_usage", language))
        return
    try:
        url = validate_url(parse_single_url_arg(command.args))
        domain = urlparse(url).hostname or ""
        route = route_name_for_url(url)
        if route == "proxy":
            http_proxy_for_target(url)
    except RoutingError:
        await message.answer(text("proxy_not_configured", language))
        return
    except (CommandArgumentError, URLValidationError, ValueError) as exc:
        await message.answer(text("request_failed", language, error=str(exc)))
        return
    await message.answer(text(
        "route_test_result", language, domain=domain, route=route_label(route, language)
    ))


@router.message(Command("cookies_help"))
async def cookies_help_handler(message: Message) -> None:
    if await reject_unless_allowed(message):
        return
    await message.answer(text("cookies_help", get_language(get_user_id(message))))


@router.message(Command("cookies_import"))
async def cookies_import_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    language = get_language(get_user_id(message))
    settings = get_settings()
    if not settings.enable_cookie_import:
        await message.answer(text("cookie_import_disabled", language))
        return
    if not settings.cookie_encryption_key:
        await message.answer(text("cookie_key_missing", language))
        return
    if not command.args:
        await message.answer(text("cookies_import_usage", language))
        return
    try:
        domain = normalize_domain(command.args.strip())
    except CookieValidationError as exc:
        await message.answer(text("request_failed", language, error=str(exc)))
        return
    user_id = get_user_id(message)
    if user_id is None:
        await message.answer(text("user_identification_failed", language))
        return
    pending_cookie_imports[user_id] = domain
    await message.answer(text("cookies_send_json", language, domain=domain))


@router.message(Command("sessions"))
async def sessions_handler(message: Message) -> None:
    if await reject_unless_allowed(message):
        return
    user_id = get_user_id(message)
    language = get_language(user_id)
    sessions = list_sessions(user_id) if user_id is not None else []
    await message.answer(
        text("sessions_list", language, sessions="\n".join(sessions))
        if sessions
        else text("sessions", language)
    )


@router.message(Command("delete_session"))
async def delete_session_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    user_id = get_user_id(message)
    language = get_language(user_id)
    if not command.args:
        await message.answer(text("delete_session_usage", language))
        return
    try:
        domain = normalize_domain(command.args.strip())
        deleted = user_id is not None and delete_session(user_id, domain)
    except CookieValidationError as exc:
        await message.answer(text("request_failed", language, error=str(exc)))
        return
    await message.answer(text(
        "session_deleted" if deleted else "session_not_found",
        language,
        domain=domain,
    ))


@router.message(Command("fetch"))
async def fetch_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    language = get_language(get_user_id(message))
    try:
        url = validate_action_url(parse_single_url_arg(command.args), "fetch")
        async with HttpFetcher(proxy_url=http_proxy_for_target(url)) as fetcher:
            response = await fetcher.fetch(url)
        body = safe_response_text(response)[:3500]
        await message.answer(
            f"{text('http_status', language, status=response.status_code)}\n\n{body}"
        )
    except CommandArgumentError:
        await message.answer(text("url_usage", language, command="fetch"))
    except PermissionError as exc:
        await message.answer(permission_error_message(exc, language))
    except RoutingError:
        await message.answer(text("proxy_not_configured", language))
    except (URLValidationError, FetchError) as exc:
        await message.answer(text("request_failed", language, error=str(exc)))


@router.message(Command("links"))
async def links_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    language = get_language(get_user_id(message))
    try:
        url = validate_action_url(parse_single_url_arg(command.args), "links")
        async with HttpFetcher(proxy_url=http_proxy_for_target(url)) as fetcher:
            response = await fetcher.fetch(url)
        links = LinkExtractor.extract(safe_response_text(response), str(response.url))
        if not links:
            await message.answer(text("no_links", language))
            return
        output = "\n".join(links[:50])
        await message.answer(output[:4000])
    except CommandArgumentError:
        await message.answer(text("url_usage", language, command="links"))
    except PermissionError as exc:
        await message.answer(permission_error_message(exc, language))
    except RoutingError:
        await message.answer(text("proxy_not_configured", language))
    except (URLValidationError, FetchError) as exc:
        await message.answer(text("request_failed", language, error=str(exc)))


@router.message(Command("html"))
async def html_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    language = get_language(get_user_id(message))
    try:
        url = validate_action_url(parse_single_url_arg(command.args), "html")
        http_proxy_for_target(url)
        job = create_background_job(message, "html", url)
        await message.answer(text(
            "job_started", language, job_id=job.id, status=job_status_text(job.status, language)
        ))
        task = asyncio.create_task(run_html_job(job, message))
        job_store.register_task(job.id, task)
    except CommandArgumentError:
        await message.answer(text("url_usage", language, command="html"))
    except PermissionError as exc:
        await message.answer(permission_error_message(exc, language))
    except RoutingError:
        await message.answer(text("proxy_not_configured", language))
    except (URLValidationError, JobLimitError) as exc:
        await message.answer(text("request_failed", language, error=str(exc)))


def create_background_job(message: Message, command: str, url: str) -> Job:
    user_id = get_user_id(message)
    if user_id is None:
        raise JobLimitError("Unable to identify the requesting user.")
    return create_background_job_for_user(user_id, command, url)


def create_background_job_for_user(user_id: int, command: str, url: str) -> Job:
    settings = get_settings()
    return job_store.create_job(
        user_id,
        command,
        url,
        settings.max_concurrent_jobs_global,
        settings.max_concurrent_jobs_per_user,
    )


def browser_cookies_for_job(job: Job) -> tuple[dict, ...]:
    return browser_cookies_for_user_url(job.user_id, job.url)


def browser_cookies_for_user_url(user_id: int, url: str) -> tuple[dict, ...]:
    hostname = urlparse(url).hostname
    if not hostname:
        return ()
    return tuple(load_cookies_for_domain(user_id, hostname))


def browser_storage_for_tab(user_id: int, tab_id: str) -> dict | None:
    return load_tab_storage_state(user_id, tab_id)


def browser_storage_for_job(job: Job) -> dict | None:
    tab_id = job_tab_ids.get(job.id)
    return browser_storage_for_tab(job.user_id, tab_id) if tab_id else None


async def run_html_job(job: Job, message: Message) -> None:
    settings = get_settings()
    language = get_language(job.user_id)
    job_store.update_job(job.id, status="running", progress=10)
    try:
        async with HttpFetcher(
            max_response_bytes=0, proxy_url=http_proxy_for_target(job.url)
        ) as fetcher:
            response = await fetcher.fetch(job.url)
        job_store.update_job(job.id, progress=60)
        output_path = save_html(
            response.content,
            str(response.url),
            Path(settings.downloads_dir),
            settings.max_html_size_mb,
            settings.min_free_disk_mb,
        )
        await message.answer_document(FSInputFile(output_path))
        cleanup_sent_file(
            output_path,
            Path(settings.downloads_dir),
            settings.delete_generated_files_after_send,
        )
        result_message = text("html_sent", language, filename=output_path.name)
        job_store.update_job(
            job.id, status="success", progress=100, result_message=result_message
        )
    except asyncio.CancelledError:
        if (current := job_store.get_job(job.id)) and current.status != "cancelled":
            job_store.update_job(job.id, status="cancelled")
        raise
    except (URLValidationError, FetchError, StorageError, OSError, TelegramAPIError) as exc:
        await fail_job(job.id, message, str(exc))
    except RoutingError:
        await fail_job(job.id, message, text("proxy_not_configured", language))
    except Exception:
        await fail_job(job.id, message, text("job_unexpected_failure", language))


@router.message(Command("html_rendered", "rendered_html"))
async def rendered_html_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    language = get_language(get_user_id(message))
    try:
        url = validate_action_url(parse_single_url_arg(command.args), "html_rendered")
        browser_proxy_for_target(url)
        job = create_background_job(message, "html_rendered", url)
        await message.answer(text(
            "job_started", language, job_id=job.id, status=job_status_text(job.status, language)
        ))
        task = asyncio.create_task(run_rendered_html_job(job, message))
        job_store.register_task(job.id, task)
    except CommandArgumentError:
        await message.answer(text("url_usage", language, command="html_rendered"))
    except PermissionError as exc:
        await message.answer(permission_error_message(exc, language))
    except RoutingError:
        await message.answer(text("proxy_not_configured", language))
    except (URLValidationError, JobLimitError) as exc:
        await message.answer(text("request_failed", language, error=str(exc)))


async def run_rendered_html_job(job: Job, message: Message) -> None:
    settings = get_settings()
    language = get_language(job.user_id)
    job_store.update_job(job.id, status="running", progress=10)
    try:
        options = RenderedHtmlOptions(
            timeout_seconds=settings.browser_timeout_seconds,
            max_html_size_mb=settings.max_html_size_mb,
            wait_until=settings.rendered_html_wait_until,
            viewport_width=settings.screenshot_viewport_width,
            viewport_height=settings.screenshot_viewport_height,
            minimum_free_mb=settings.min_free_disk_mb,
            cookies=browser_cookies_for_job(job),
            proxy_server=browser_proxy_for_target(job.url),
            storage_state=browser_storage_for_job(job),
        )
        result = await export_rendered_html(
            job.url, Path(settings.downloads_dir), options
        )
        job_store.update_job(job.id, progress=90)
        await message.answer_document(
            FSInputFile(result.path),
            caption=(
                f"{text('filename_label', language)}: {result.filename}\n"
                f"{text('size_label', language)}: {result.size_bytes} bytes\n"
                f"{text('final_url_label', language)}: {result.final_url}\n"
                f"{text('compressed_label', language)}: "
                f"{text('yes' if result.compressed else 'no', language)}"
            ),
        )
        cleanup_sent_file(
            result.path,
            Path(settings.downloads_dir),
            settings.delete_generated_files_after_send,
        )
        job_store.update_job(
            job.id,
            status="success",
            progress=100,
            result_message=text("rendered_html_sent", language, filename=result.filename),
        )
        job_tab_ids.pop(job.id, None)
    except asyncio.CancelledError:
        job_tab_ids.pop(job.id, None)
        if (current := job_store.get_job(job.id)) and current.status != "cancelled":
            job_store.update_job(job.id, status="cancelled")
        raise
    except NotImplementedError as exc:
        safe_message = map_browser_runtime_error(exc) or text("browser_request_failed", language)
        log_safe_job_error(job, exc, safe_message)
        await fail_job(job.id, message, safe_message)
    except (
        URLValidationError,
        RenderedHtmlBrowserNotInstalledError,
        RenderedHtmlTimeoutError,
        RenderedHtmlError,
        EncryptionError,
        StorageError,
        OSError,
    ) as exc:
        log_safe_job_error(job, exc, str(exc))
        await fail_job(job.id, message, str(exc))
    except TelegramAPIError as exc:
        safe_message = text("telegram_rendered_html_failed", language)
        log_safe_job_error(job, exc, safe_message)
        await fail_job(job.id, message, safe_message)
    except RoutingError:
        await fail_job(job.id, message, text("proxy_not_configured", language))
    except Exception as exc:
        safe_message = text("browser_request_failed", language)
        log_safe_job_error(job, exc, safe_message)
        await fail_job(job.id, message, safe_message)


def format_download_info(
    filename: str, content_type: str, size: int, sha256: str, language: str = "en"
) -> str:
    return (
        f"{text('filename_label', language)}: {filename}\n"
        f"{text('content_type_label', language)}: {content_type}\n"
        f"{text('size_label', language)}: {size} bytes\n"
        f"{text('sha256_label', language)}: {sha256}"
    )


@router.message(Command("download"))
async def download_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    user_id = get_user_id(message)
    language = get_language(user_id)
    settings = get_settings()
    if user_id is None or download_quota.remaining(
        user_id, settings.max_downloads_per_user_per_day
    ) <= 0:
        await message.answer(text("daily_quota_exceeded", language))
        return

    try:
        url = validate_action_url(parse_single_url_arg(command.args), "download")
        http_proxy_for_target(url)
        job = create_background_job(message, "download", url)
        download_quota.consume(user_id, settings.max_downloads_per_user_per_day)
        await message.answer(text(
            "job_started", language, job_id=job.id, status=job_status_text(job.status, language)
        ))
        task = asyncio.create_task(run_download_job(job, message))
        job_store.register_task(job.id, task)
    except CommandArgumentError:
        await message.answer(text("url_usage", language, command="download"))
    except PermissionError as exc:
        await message.answer(permission_error_message(exc, language))
    except RoutingError:
        await message.answer(text("proxy_not_configured", language))
    except (URLValidationError, JobLimitError) as exc:
        await message.answer(text("request_failed", language, error=str(exc)))


async def run_download_job(job: Job, message: Message) -> None:
    settings = get_settings()
    language = get_language(job.user_id)
    job_store.update_job(job.id, status="running", progress=10)
    try:
        async with FileDownloader(proxy_url=http_proxy_for_target(job.url)) as downloader:
            result = await downloader.download(
                job.url,
                Path(settings.downloads_dir),
                settings.max_download_size_mb,
                settings.min_free_disk_mb,
            )
        job_store.update_job(job.id, progress=80)
        info = format_download_info(
            result.filename, result.content_type, result.size, result.sha256, language
        )
        upload_limit = settings.telegram_max_upload_size_mb * 1024 * 1024
        if result.size > upload_limit:
            await message.answer(
                f"{info}\n\n{text('upload_limit_exceeded', language)}"
            )
            result_message = text("upload_limit_result", language)
        else:
            await message.answer_document(FSInputFile(result.path), caption=info)
            cleanup_sent_file(
                result.path,
                Path(settings.downloads_dir),
                settings.delete_generated_files_after_send,
            )
            result_message = text("download_sent", language, filename=result.filename)
        job_store.update_job(
            job.id, status="success", progress=100, result_message=result_message
        )
    except asyncio.CancelledError:
        if (current := job_store.get_job(job.id)) and current.status != "cancelled":
            job_store.update_job(job.id, status="cancelled")
        raise
    except TelegramAPIError as exc:
        safe_message = text("telegram_upload_failed", language)
        log_safe_job_error(job, exc, safe_message)
        await fail_job(job.id, message, safe_message)
    except (URLValidationError, DownloadError, StorageError, OSError) as exc:
        safe_error = (
            text("direct_file_only", language)
            if "only supports direct file links" in str(exc)
            else str(exc)
        )
        await fail_job(job.id, message, safe_error)
    except RoutingError:
        await fail_job(job.id, message, text("proxy_not_configured", language))
    except Exception:
        await fail_job(job.id, message, text("job_unexpected_failure", language))


@router.message(Command("screenshot"))
async def screenshot_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    language = get_language(get_user_id(message))
    try:
        url = validate_action_url(parse_single_url_arg(command.args), "screenshot")
        browser_proxy_for_target(url)
        job = create_background_job(message, "screenshot", url)
        await message.answer(text(
            "job_started", language, job_id=job.id, status=job_status_text(job.status, language)
        ))
        task = asyncio.create_task(run_screenshot_job(job, message))
        job_store.register_task(job.id, task)
    except CommandArgumentError:
        await message.answer(text("url_usage", language, command="screenshot"))
    except PermissionError as exc:
        await message.answer(permission_error_message(exc, language))
    except RoutingError:
        await message.answer(text("proxy_not_configured", language))
    except (URLValidationError, JobLimitError) as exc:
        await message.answer(text("request_failed", language, error=str(exc)))


async def run_screenshot_job(job: Job, message: Message) -> None:
    settings = get_settings()
    language = get_language(job.user_id)
    job_store.update_job(job.id, status="running", progress=10)
    try:
        options = ScreenshotOptions(
            timeout_seconds=settings.browser_timeout_seconds,
            viewport_width=settings.screenshot_viewport_width,
            viewport_height=settings.screenshot_viewport_height,
            max_size_mb=settings.max_screenshot_size_mb,
            minimum_free_mb=settings.min_free_disk_mb,
            cookies=browser_cookies_for_job(job),
            proxy_server=browser_proxy_for_target(job.url),
            storage_state=browser_storage_for_job(job),
        )
        result = await capture_screenshot(
            job.url, Path(settings.downloads_dir), options
        )
        job_store.update_job(job.id, progress=90)
        await message.answer_document(
            FSInputFile(result.path),
            caption=(
                f"{text('filename_label', language)}: {result.filename}\n"
                f"{text('size_label', language)}: {result.size_bytes} bytes\n"
                f"{text('final_url_label', language)}: {result.final_url}"
            ),
        )
        cleanup_sent_file(
            result.path,
            Path(settings.downloads_dir),
            settings.delete_generated_files_after_send,
        )
        job_store.update_job(
            job.id,
            status="success",
            progress=100,
            result_message=text("screenshot_sent", language, filename=result.filename),
        )
        job_tab_ids.pop(job.id, None)
    except asyncio.CancelledError:
        job_tab_ids.pop(job.id, None)
        if (current := job_store.get_job(job.id)) and current.status != "cancelled":
            job_store.update_job(job.id, status="cancelled")
        raise
    except NotImplementedError as exc:
        safe_message = map_browser_runtime_error(exc) or text("browser_request_failed", language)
        log_safe_job_error(job, exc, safe_message)
        await fail_job(job.id, message, safe_message)
    except (
        URLValidationError,
        BrowserNotInstalledError,
        ScreenshotTimeoutError,
        ScreenshotTooLargeError,
        ScreenshotError,
        EncryptionError,
        StorageError,
        OSError,
    ) as exc:
        log_safe_job_error(job, exc, str(exc))
        await fail_job(job.id, message, str(exc))
    except TelegramAPIError as exc:
        safe_message = text("telegram_screenshot_failed", language)
        log_safe_job_error(job, exc, safe_message)
        await fail_job(job.id, message, safe_message)
    except RoutingError:
        await fail_job(job.id, message, text("proxy_not_configured", language))
    except Exception as exc:
        safe_message = text("browser_request_failed", language)
        log_safe_job_error(job, exc, safe_message)
        await fail_job(job.id, message, safe_message)


@router.message(Command("pdf"))
async def pdf_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    language = get_language(get_user_id(message))
    try:
        url = validate_action_url(parse_single_url_arg(command.args), "pdf")
        browser_proxy_for_target(url)
        job = create_background_job(message, "pdf", url)
        await message.answer(text(
            "job_started", language, job_id=job.id, status=job_status_text(job.status, language)
        ))
        task = asyncio.create_task(run_pdf_job(job, message))
        job_store.register_task(job.id, task)
    except CommandArgumentError:
        await message.answer(text("url_usage", language, command="pdf"))
    except PermissionError as exc:
        await message.answer(permission_error_message(exc, language))
    except RoutingError:
        await message.answer(text("proxy_not_configured", language))
    except (URLValidationError, JobLimitError) as exc:
        await message.answer(text("request_failed", language, error=str(exc)))


async def run_pdf_job(job: Job, message: Message) -> None:
    settings = get_settings()
    language = get_language(job.user_id)
    job_store.update_job(job.id, status="running", progress=10)
    try:
        options = PdfOptions(
            timeout_seconds=settings.browser_timeout_seconds,
            format=settings.pdf_format,
            print_background=settings.pdf_print_background,
            max_size_mb=settings.max_pdf_size_mb,
            minimum_free_mb=settings.min_free_disk_mb,
            cookies=browser_cookies_for_job(job),
            proxy_server=browser_proxy_for_target(job.url),
            storage_state=browser_storage_for_job(job),
        )
        result = await export_pdf(job.url, Path(settings.downloads_dir), options)
        job_store.update_job(job.id, progress=90)
        await message.answer_document(
            FSInputFile(result.path),
            caption=(
                f"{text('filename_label', language)}: {result.filename}\n"
                f"{text('size_label', language)}: {result.size_bytes} bytes\n"
                f"{text('final_url_label', language)}: {result.final_url}"
            ),
        )
        cleanup_sent_file(
            result.path,
            Path(settings.downloads_dir),
            settings.delete_generated_files_after_send,
        )
        job_store.update_job(
            job.id,
            status="success",
            progress=100,
            result_message=text("pdf_sent", language, filename=result.filename),
        )
        job_tab_ids.pop(job.id, None)
    except asyncio.CancelledError:
        job_tab_ids.pop(job.id, None)
        if (current := job_store.get_job(job.id)) and current.status != "cancelled":
            job_store.update_job(job.id, status="cancelled")
        raise
    except NotImplementedError as exc:
        safe_message = map_browser_runtime_error(exc) or text("browser_request_failed", language)
        log_safe_job_error(job, exc, safe_message)
        await fail_job(job.id, message, safe_message)
    except (
        URLValidationError,
        PdfBrowserNotInstalledError,
        PdfTimeoutError,
        PdfTooLargeError,
        PdfError,
        EncryptionError,
        StorageError,
        OSError,
    ) as exc:
        log_safe_job_error(job, exc, str(exc))
        await fail_job(job.id, message, str(exc))
    except TelegramAPIError as exc:
        safe_message = text("telegram_pdf_failed", language)
        log_safe_job_error(job, exc, safe_message)
        await fail_job(job.id, message, safe_message)
    except RoutingError:
        await fail_job(job.id, message, text("proxy_not_configured", language))
    except Exception as exc:
        safe_message = text("browser_request_failed", language)
        log_safe_job_error(job, exc, safe_message)
        await fail_job(job.id, message, safe_message)


async def fail_job(job_id: str, message: Message, error: str) -> None:
    job_tab_ids.pop(job_id, None)
    job_store.update_job(job_id, status="failed", error_message=error)
    await message.answer(text(
        "job_failed", get_language(get_user_id(message)), job_id=job_id, error=error
    ))


def log_safe_job_error(job: Job, error: BaseException, safe_message: str) -> None:
    logger.warning(
        "Background job failed: job_id=%s command=%s exception_type=%s safe_message=%s",
        job.id,
        job.command,
        type(error).__name__,
        safe_message,
    )


def job_status_text(status: str, language: str) -> str:
    return text(f"job_status_{status}", language)


def format_job(job: Job, language: str = "en") -> str:
    details = [
        f"{text('job_id_label', language)}: {job.id}",
        f"{text('command_label', language)}: /{job.command}",
        f"{text('status_label', language)}: {job_status_text(job.status, language)}",
        f"{text('progress_label', language)}: {job.progress}%",
    ]
    if job.result_message:
        details.append(f"{text('result_label', language)}: {job.result_message}")
    if job.error_message:
        details.append(f"{text('error_label', language)}: {job.error_message}")
    return "\n".join(details)


def format_job_history(job: JobHistoryEntry, language: str = "en") -> str:
    details = [
        f"{text('job_id_label', language)}: {job.job_id}",
        f"{text('command_label', language)}: /{job.command}",
        f"{text('status_label', language)}: {job_status_text(job.status, language)}",
    ]
    if job.url_domain:
        details.append(f"{text('domain_label', language)}: {job.url_domain}")
    if job.error_message:
        details.append(f"{text('error_label', language)}: {job.error_message}")
    return "\n".join(details)


def get_job_status_record(
    job_id: str,
    user_id: int,
    is_admin_user: bool,
    store: JobStore,
    history_path: Path,
) -> Job | JobHistoryEntry | None:
    active_job = store.get_job(job_id)
    if active_job is not None:
        return active_job if is_admin_user or active_job.user_id == user_id else None
    history_job = find_job_history(history_path, job_id)
    if history_job is None:
        return None
    return history_job if is_admin_user or history_job.user_id == user_id else None


def list_job_records(
    user_id: int,
    is_admin_user: bool,
    store: JobStore,
    history_path: Path,
) -> list[Job | JobHistoryEntry]:
    active_jobs = store.list_jobs() if is_admin_user else store.list_user_jobs(user_id)
    history_jobs = (
        load_job_history(history_path)
        if is_admin_user
        else list_user_job_history(history_path, user_id)
    )
    active_ids = {job.id for job in active_jobs}
    combined: list[Job | JobHistoryEntry] = active_jobs + [
        job for job in history_jobs if job.job_id not in active_ids
    ]
    return sorted(combined, key=lambda job: job.created_at, reverse=True)


@router.message(Command("status"))
async def status_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    user_id = get_user_id(message)
    language = get_language(user_id)
    if not command.args:
        await message.answer(text("status_usage", language))
        return
    if user_id is None:
        await message.answer(text("job_not_found", language))
        return
    job = get_job_status_record(
        command.args.strip(),
        user_id,
        is_admin(user_id),
        job_store,
        Path(get_settings().job_history_path),
    )
    if job is None:
        await message.answer(text("job_not_found", language))
        return
    await message.answer(
        format_job(job, language)
        if isinstance(job, Job)
        else format_job_history(job, language)
    )


@router.message(Command("jobs"))
async def jobs_handler(message: Message) -> None:
    if await reject_unless_allowed(message):
        return
    user_id = get_user_id(message)
    language = get_language(user_id)
    if user_id is None:
        await message.answer(text("no_jobs", language))
        return
    jobs = list_job_records(
        user_id,
        is_admin(user_id),
        job_store,
        Path(get_settings().job_history_path),
    )
    if not jobs:
        await message.answer(text("no_jobs", language))
        return
    await message.answer(
        "\n\n".join(
            format_job(job, language)
            if isinstance(job, Job)
            else format_job_history(job, language)
            for job in jobs[:10]
        )
    )


@router.message(Command("cancel"))
async def cancel_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    user_id = get_user_id(message)
    language = get_language(user_id)
    if not command.args:
        await message.answer(text("cancel_usage", language))
        return
    if user_id is None or not job_store.cancel_job(
        command.args.strip(), user_id, is_admin(user_id)
    ):
        await message.answer(text("job_cancel_failed", language))
        return
    await message.answer(
        text("job_cancelled", language, job_id=command.args.strip())
    )


@router.callback_query(F.data.startswith("interact:"))
async def interaction_callback_handler(callback: CallbackQuery) -> None:
    user_id = callback.from_user.id
    language = get_language(user_id)
    parts = (callback.data or "").split(":")
    if len(parts) != 3 or not parts[2].isdigit():
        await callback.answer(text("invalid_action", language), show_alert=True)
        return
    session_id, index = parts[1], int(parts[2])
    elements = pending_interactions.get((user_id, session_id))
    if elements is None or index >= len(elements):
        await callback.answer(text("interaction_expired", language), show_alert=True)
        return
    try:
        session = url_session_store.get_for_user(
            session_id, user_id, get_settings().url_session_ttl_minutes
        )
        element = elements[index]
        result = await activate_interactive_element(
            session.url,
            element,
            get_settings().interaction_timeout_seconds,
            browser_cookies_for_user_url(user_id, session.url),
            browser_proxy_for_target(session.url),
            browser_storage_for_tab(user_id, session_id),
        )
        invalidate_page_options(user_id, session_id)
        validate_action_url(result.final_url)
        updated = url_session_store.navigate(
            session_id, user_id, result.final_url, result.title
        )
    except Exception as exc:
        logger.warning("Interaction activation failed: exception_type=%s", type(exc).__name__)
        await callback.answer(text("interaction_failed", language), show_alert=True)
        return
    state_saved = False
    try:
        if result.storage_state is not None:
            state_saved = save_tab_storage_state(
                user_id, session_id, result.storage_state
            )
    except (EncryptionError, OSError, ValueError) as exc:
        logger.warning(
            "Browser tab state could not be saved: tab_id=%s exception_type=%s",
            session_id,
            type(exc).__name__,
        )
    await callback.answer()
    if callback.message is not None and updated is not None:
        await callback.message.edit_text(
            text(
                "url_refreshed",
                language,
                title=updated.title or urlparse(updated.url).hostname or updated.url,
                url=updated.url,
            ),
            reply_markup=url_action_keyboard(updated.session_id, language),
        )
        await callback.message.answer(text("page_option_applied", language))
        if not state_saved:
            await callback.message.answer(text("page_state_not_saved", language))


@router.message()
async def text_message_handler(message: Message) -> None:
    user_id = get_user_id(message)
    if user_id is None or not message.text:
        return
    if user_id in pending_cookie_imports:
        if not is_allowed_user(user_id):
            pending_cookie_imports.pop(user_id, None)
            await message.answer(text("access_denied", get_language(user_id)))
            return

        settings = get_settings()
        domain = pending_cookie_imports[user_id]
        if not settings.enable_cookie_import:
            pending_cookie_imports.pop(user_id, None)
            await message.answer(text("cookie_import_disabled", get_language(user_id)))
            return
        if not settings.cookie_encryption_key:
            pending_cookie_imports.pop(user_id, None)
            await message.answer(text("cookie_key_missing", get_language(user_id)))
            return
        try:
            cookies = validate_cookies_json(
                message.text, domain, settings.max_cookie_import_size_kb
            )
            save_cookies(user_id, domain, json.dumps(cookies, separators=(",", ":")))
        except (CookieValidationError, EncryptionError, OSError) as exc:
            await message.answer(
                text("request_failed", get_language(user_id), error=str(exc))
            )
            return

        pending_cookie_imports.pop(user_id, None)
        await message.answer(text("cookies_saved", get_language(user_id), domain=domain))
        return

    language = get_language(user_id)
    pending = consume_user_input(user_id)
    if pending == "search":
        try:
            query = validate_search_query(
                message.text, get_settings().search_query_max_length
            )
            await send_search_results(message, user_id, query, language)
        except SearchQueryError:
            await message.answer(text("search_usage", language))
        except SearchDisabledError:
            await message.answer(text("search_disabled", language))
        except SearchConfigurationError:
            await message.answer(text("search_misconfigured", language))
        except PermissionError as exc:
            await message.answer(permission_error_message(exc, language))
        except Exception:
            await message.answer(text("search_unavailable", language))
        return
    if pending == "url":
        url = detect_plain_url(message.text)
        if url is None:
            await message.answer(text("invalid_url", language))
            return
        await create_url_card(message, user_id, url)
        return

    stripped = message.text.strip()
    if not stripped.lower().startswith(("http://", "https://")):
        return
    if not is_allowed_user(user_id):
        await message.answer(text("access_denied", language))
        return
    url = detect_plain_url(message.text)
    if url is None:
        await message.answer(text("invalid_url", language))
        return
    await create_url_card(message, user_id, url)
