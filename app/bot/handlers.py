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
from app.core.command_args import CommandArgumentError, parse_single_url_arg, url_usage
from app.core.cleanup import cleanup_generated_files
from app.core.encryption import EncryptionError
from app.core.jobs import Job, JobLimitError, job_store
from app.core.session_store import (
    delete_session,
    list_sessions,
    load_cookies_for_domain,
    save_cookies,
)
from app.core.runtime_status import RUNTIME_TARGET, build_admin_status
from app.core.storage import StorageError
from app.core.temp_files import cleanup_sent_file
from app.core.url_sessions import (
    URLSessionExpired,
    URLSessionNotFound,
    URLSessionNotOwned,
    url_session_store,
)
from app.core.url_validation import URLValidationError, validate_url
from app.bot.i18n import get_language, set_language, text
from app.bot.ui import (
    detect_plain_url,
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
from app.fetchers.html_export import save_html
from app.fetchers.link_extractor import LinkExtractor
from app.version import APP_VERSION

router = Router()
logger = logging.getLogger(__name__)

HELP_TEXT = text("help", "en")

ADMIN_REQUIRED = "Admin access required."
pending_cookie_imports: dict[int, str] = {}


def get_user_id(message: Message) -> int | None:
    return message.from_user.id if message.from_user else None


async def reject_unless_allowed(message: Message) -> bool:
    user_id = get_user_id(message)
    if user_id is None or not is_allowed_user(user_id):
        await message.answer(text("access_denied", get_language(user_id)))
        return True
    return False


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    language = get_language(get_user_id(message))
    await message.answer(text("welcome", language), reply_markup=menu_keyboard(language))


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    language = get_language(get_user_id(message))
    await message.answer(text("help", language), reply_markup=menu_keyboard(language))


@router.message(Command("menu"))
async def menu_handler(message: Message) -> None:
    language = get_language(get_user_id(message))
    await message.answer(text("menu", language), reply_markup=menu_keyboard(language))


@router.message(Command("about"))
async def about_handler(message: Message) -> None:
    language = get_language(get_user_id(message))
    await message.answer(
        text(
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
        await callback.message.answer(text("open_url", language))
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
    elif action == "account":
        await callback.message.answer(
            text(
                "account",
                language,
                user_id=user_id,
                admin=text("yes" if is_admin(user_id) else "no", language),
                access=text("yes" if is_allowed_user(user_id) else "no", language),
                language=language,
            )
        )
    elif action == "help":
        await callback.message.answer(
            text("help", language), reply_markup=menu_keyboard(language)
        )
    elif action == "search":
        await callback.message.answer(text("search_planned", language))


async def create_url_card(message: Message, user_id: int, url: str) -> None:
    language = get_language(user_id)
    session = url_session_store.create(user_id, url)
    sent = await message.answer(
        text("url_card", language, url=url),
        reply_markup=url_action_keyboard(session.session_id, language),
    )
    url_session_store.touch(session.session_id, sent.message_id)


@router.callback_query(F.data.startswith("url:"))
async def url_action_callback_handler(callback: CallbackQuery) -> None:
    parsed = parse_url_callback_data(callback.data)
    if parsed is None:
        await callback.answer("Invalid action", show_alert=True)
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
        validate_url(session.url)
    except (URLSessionNotFound, URLSessionExpired):
        await callback.answer(text("session_expired", language), show_alert=True)
        return
    except URLSessionNotOwned:
        await callback.answer(text("session_not_owned", language), show_alert=True)
        return
    except URLValidationError:
        await callback.answer(text("invalid_url", language), show_alert=True)
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
            text("url_refreshed", language, url=session.url),
            reply_markup=url_action_keyboard(session.session_id, language),
        )
        return
    if parsed.action == "links":
        try:
            async with HttpFetcher() as fetcher:
                response = await fetcher.fetch(session.url)
            links = LinkExtractor.extract(
                safe_response_text(response), str(response.url)
            )
            await message.answer(
                "\n".join(links[:50])[:4000] if links else text("no_links", language)
            )
        except (URLValidationError, FetchError) as exc:
            await message.answer(text("request_failed", language, error=str(exc)))
        return

    command = "html_rendered" if parsed.action == "rendered_html" else parsed.action
    settings = get_settings()
    if command == "download":
        if download_quota.remaining(
            user_id, settings.max_downloads_per_user_per_day
        ) <= 0:
            await message.answer("Daily download quota exceeded. Try again tomorrow.")
            return
    try:
        job = create_background_job_for_user(user_id, command, session.url)
        if command == "download":
            download_quota.consume(user_id, settings.max_downloads_per_user_per_day)
        await message.answer(
            text("job_started", language, job_id=job.id, status=job.status)
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


@router.message(Command("whoami"))
async def whoami_handler(message: Message) -> None:
    user_id = get_user_id(message)
    await message.answer(f"Your Telegram ID: {user_id}" if user_id else "User ID unavailable")


@router.message(Command("access"))
async def access_handler(message: Message) -> None:
    user_id = get_user_id(message)
    if user_id is None or not is_admin(user_id):
        await message.answer(ADMIN_REQUIRED)
        return
    settings = get_settings()
    static_allowed = parse_telegram_ids(settings.allowed_telegram_ids)
    runtime_allowed = list_allowed_users(Path(settings.access_storage_path))
    await message.answer(
        f"Your Telegram ID: {user_id}\n"
        f"Admin: yes\n"
        f"Runtime access management: "
        f"{'enabled' if settings.enable_runtime_access_management else 'disabled'}\n"
        f"Static allowed users: {len(static_allowed)}\n"
        f"Runtime allowed users: {len(runtime_allowed)}"
    )


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
    if user_id is None or not is_admin(user_id):
        await message.answer(ADMIN_REQUIRED)
        return None
    if not get_settings().enable_runtime_access_management:
        await message.answer("Runtime access management is disabled.")
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
        await message.answer(f"Error: {exc}")
        return
    added = add_allowed_user(runtime_access_path(), telegram_id, admin_id, note)
    await message.answer(
        f"Access granted to {telegram_id}."
        if added
        else f"User {telegram_id} is already runtime-allowed."
    )


@router.message(Command("deny"))
async def deny_handler(message: Message, command: CommandObject) -> None:
    admin_id = await require_runtime_admin(message)
    if admin_id is None:
        return
    try:
        telegram_id, _ = parse_access_target(command.args)
    except ValueError as exc:
        await message.answer(f"Error: {exc}")
        return
    try:
        removed = deny_runtime_user(runtime_access_path(), telegram_id)
    except ValueError as exc:
        await message.answer(f"{exc}.")
        return
    await message.answer(
        f"Runtime access revoked for {telegram_id}."
        if removed
        else "Runtime allowed user not found."
    )


@router.message(Command("allowed_users"))
async def allowed_users_handler(message: Message) -> None:
    if await require_runtime_admin(message) is None:
        return
    settings = get_settings()
    static_ids = sorted(parse_telegram_ids(settings.allowed_telegram_ids))
    runtime_users = list_allowed_users(runtime_access_path())
    static_text = ", ".join(map(str, static_ids)) if static_ids else "none"
    runtime_text = "\n".join(
        f"{user.telegram_id}"
        + (f" - {user.note}" if user.note else "")
        for user in runtime_users
    ) or "none"
    await message.answer(
        f"Static allowed users: {static_text}\nRuntime allowed users:\n{runtime_text}"
    )


@router.message(Command("admin_status"))
async def admin_status_handler(message: Message) -> None:
    user_id = get_user_id(message)
    if user_id is None or not is_admin(user_id):
        await message.answer(ADMIN_REQUIRED)
        return
    status = build_admin_status(get_settings(), job_store)
    directories = ", ".join(
        f"{name}={'ready' if exists else 'missing'}"
        for name, exists in status.generated_directories.items()
    )
    await message.answer(
        f"Version: {status.version}\n"
        f"Runtime target: {status.runtime_target}\n"
        f"Active jobs: {status.active_jobs}\n"
        f"Known jobs: {status.known_jobs}\n"
        f"Runtime allowed users: {status.runtime_allowed_users}\n"
        f"Storage free: {status.storage_free_bytes} bytes\n"
        f"Cookie import: {'enabled' if status.cookie_import_enabled else 'disabled'}\n"
        f"Generated directories: {directories}"
    )


@router.message(Command("cleanup"))
async def cleanup_handler(message: Message) -> None:
    user_id = get_user_id(message)
    if user_id is None or not is_admin(user_id):
        await message.answer(ADMIN_REQUIRED)
        return
    settings = get_settings()
    try:
        result = cleanup_generated_files(
            Path(settings.downloads_dir), settings.cleanup_max_age_hours
        )
    except OSError:
        await message.answer("Cleanup failed because generated files could not be removed.")
        return
    await message.answer(
        f"Cleanup complete.\nDeleted files: {result.deleted_files}\n"
        f"Freed bytes: {result.freed_bytes}"
    )


@router.message(Command("cookies_help"))
async def cookies_help_handler(message: Message) -> None:
    if await reject_unless_allowed(message):
        return
    await message.answer(
        "Use /cookies_import <domain>, then send a Playwright-compatible JSON list. "
        "Each cookie requires name, value, and domain. Cookie values are never echoed."
    )


@router.message(Command("cookies_import"))
async def cookies_import_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    settings = get_settings()
    if not settings.enable_cookie_import:
        await message.answer("Cookie import is disabled.")
        return
    if not settings.cookie_encryption_key:
        await message.answer(
            "Cookie encryption key is not configured. Ask the bot owner to configure it."
        )
        return
    if not command.args:
        await message.answer("Usage: /cookies_import <domain>")
        return
    try:
        domain = normalize_domain(command.args.strip())
    except CookieValidationError as exc:
        await message.answer(f"Error: {exc}")
        return
    user_id = get_user_id(message)
    if user_id is None:
        await message.answer("Unable to identify the requesting user.")
        return
    pending_cookie_imports[user_id] = domain
    await message.answer(
        f"Send the JSON cookie list for {domain} in your next message."
    )


@router.message(Command("sessions"))
async def sessions_handler(message: Message) -> None:
    if await reject_unless_allowed(message):
        return
    user_id = get_user_id(message)
    sessions = list_sessions(user_id) if user_id is not None else []
    await message.answer(
        "Saved sessions:\n" + "\n".join(sessions)
        if sessions
        else "No saved sessions."
    )


@router.message(Command("delete_session"))
async def delete_session_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    if not command.args:
        await message.answer("Usage: /delete_session <domain>")
        return
    user_id = get_user_id(message)
    try:
        domain = normalize_domain(command.args.strip())
        deleted = user_id is not None and delete_session(user_id, domain)
    except CookieValidationError as exc:
        await message.answer(f"Error: {exc}")
        return
    await message.answer(
        f"Session deleted for {domain}" if deleted else "Session not found."
    )


@router.message(Command("fetch"))
async def fetch_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    try:
        url = parse_single_url_arg(command.args)
        async with HttpFetcher() as fetcher:
            response = await fetcher.fetch(url)
        body = safe_response_text(response)[:3500]
        await message.answer(f"Status: {response.status_code}\n\n{body}")
    except CommandArgumentError:
        await message.answer(url_usage("fetch"))
    except (URLValidationError, FetchError) as exc:
        await message.answer(f"Error: {exc}")


@router.message(Command("links"))
async def links_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    try:
        url = parse_single_url_arg(command.args)
        async with HttpFetcher() as fetcher:
            response = await fetcher.fetch(url)
        links = LinkExtractor.extract(safe_response_text(response), str(response.url))
        if not links:
            await message.answer("No links found.")
            return
        text = "\n".join(links[:50])
        await message.answer(text[:4000])
    except CommandArgumentError:
        await message.answer(url_usage("links"))
    except (URLValidationError, FetchError) as exc:
        await message.answer(f"Error: {exc}")


@router.message(Command("html"))
async def html_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    try:
        url = validate_url(parse_single_url_arg(command.args))
        job = create_background_job(message, "html", url)
        await message.answer(f"Job ID: {job.id}\nStatus: {job.status}")
        task = asyncio.create_task(run_html_job(job, message))
        job_store.register_task(job.id, task)
    except CommandArgumentError:
        await message.answer(url_usage("html"))
    except (URLValidationError, JobLimitError) as exc:
        await message.answer(f"Error: {exc}")


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
    hostname = urlparse(job.url).hostname
    if not hostname:
        return ()
    return tuple(load_cookies_for_domain(job.user_id, hostname))


async def run_html_job(job: Job, message: Message) -> None:
    settings = get_settings()
    job_store.update_job(job.id, status="running", progress=10)
    try:
        async with HttpFetcher(max_response_bytes=0) as fetcher:
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
        result_message = f"HTML saved and sent: {output_path.name}"
        job_store.update_job(
            job.id, status="success", progress=100, result_message=result_message
        )
    except asyncio.CancelledError:
        if (current := job_store.get_job(job.id)) and current.status != "cancelled":
            job_store.update_job(job.id, status="cancelled")
        raise
    except (URLValidationError, FetchError, StorageError, OSError, TelegramAPIError) as exc:
        await fail_job(job.id, message, str(exc))
    except Exception:
        await fail_job(job.id, message, "Job failed unexpectedly")


@router.message(Command("html_rendered", "rendered_html"))
async def rendered_html_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    try:
        url = validate_url(parse_single_url_arg(command.args))
        job = create_background_job(message, "html_rendered", url)
        await message.answer(f"Job ID: {job.id}\nStatus: {job.status}")
        task = asyncio.create_task(run_rendered_html_job(job, message))
        job_store.register_task(job.id, task)
    except CommandArgumentError:
        await message.answer(url_usage("html_rendered"))
    except (URLValidationError, JobLimitError) as exc:
        await message.answer(f"Error: {exc}")


async def run_rendered_html_job(job: Job, message: Message) -> None:
    settings = get_settings()
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
        )
        result = await export_rendered_html(
            job.url, Path(settings.downloads_dir), options
        )
        job_store.update_job(job.id, progress=90)
        await message.answer_document(
            FSInputFile(result.path),
            caption=(
                f"Filename: {result.filename}\n"
                f"Size: {result.size_bytes} bytes\n"
                f"Final URL: {result.final_url}\n"
                f"Compressed: {'yes' if result.compressed else 'no'}"
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
            result_message=f"Rendered HTML exported and sent: {result.filename}",
        )
    except asyncio.CancelledError:
        if (current := job_store.get_job(job.id)) and current.status != "cancelled":
            job_store.update_job(job.id, status="cancelled")
        raise
    except NotImplementedError as exc:
        safe_message = map_browser_runtime_error(exc) or "Browser request failed"
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
        safe_message = "Telegram could not send the rendered HTML file"
        log_safe_job_error(job, exc, safe_message)
        await fail_job(job.id, message, safe_message)
    except Exception as exc:
        safe_message = "Browser request failed"
        log_safe_job_error(job, exc, safe_message)
        await fail_job(job.id, message, safe_message)


def format_download_info(
    filename: str, content_type: str, size: int, sha256: str
) -> str:
    return (
        f"Filename: {filename}\n"
        f"Content type: {content_type}\n"
        f"Size: {size} bytes\n"
        f"SHA256: {sha256}"
    )


@router.message(Command("download"))
async def download_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    user_id = get_user_id(message)
    settings = get_settings()
    if user_id is None or download_quota.remaining(
        user_id, settings.max_downloads_per_user_per_day
    ) <= 0:
        await message.answer("Daily download quota exceeded. Try again tomorrow.")
        return

    try:
        url = validate_url(parse_single_url_arg(command.args))
        job = create_background_job(message, "download", url)
        download_quota.consume(user_id, settings.max_downloads_per_user_per_day)
        await message.answer(f"Job ID: {job.id}\nStatus: {job.status}")
        task = asyncio.create_task(run_download_job(job, message))
        job_store.register_task(job.id, task)
    except CommandArgumentError:
        await message.answer(url_usage("download"))
    except (URLValidationError, JobLimitError) as exc:
        await message.answer(f"Error: {exc}")


async def run_download_job(job: Job, message: Message) -> None:
    settings = get_settings()
    job_store.update_job(job.id, status="running", progress=10)
    try:
        async with FileDownloader() as downloader:
            result = await downloader.download(
                job.url,
                Path(settings.downloads_dir),
                settings.max_download_size_mb,
                settings.min_free_disk_mb,
            )
        job_store.update_job(job.id, progress=80)
        info = format_download_info(
            result.filename, result.content_type, result.size, result.sha256
        )
        upload_limit = settings.telegram_max_upload_size_mb * 1024 * 1024
        if result.size > upload_limit:
            await message.answer(
                f"{info}\n\nFile saved locally but exceeds the Telegram upload limit."
            )
            result_message = "File saved locally; Telegram upload limit exceeded."
        else:
            await message.answer_document(FSInputFile(result.path), caption=info)
            cleanup_sent_file(
                result.path,
                Path(settings.downloads_dir),
                settings.delete_generated_files_after_send,
            )
            result_message = f"File downloaded and sent: {result.filename}"
        job_store.update_job(
            job.id, status="success", progress=100, result_message=result_message
        )
    except asyncio.CancelledError:
        if (current := job_store.get_job(job.id)) and current.status != "cancelled":
            job_store.update_job(job.id, status="cancelled")
        raise
    except TelegramAPIError as exc:
        safe_message = "Telegram could not accept the upload. The file remains saved locally."
        log_safe_job_error(job, exc, safe_message)
        await fail_job(job.id, message, safe_message)
    except (URLValidationError, DownloadError, StorageError, OSError) as exc:
        await fail_job(job.id, message, str(exc))
    except Exception:
        await fail_job(job.id, message, "Job failed unexpectedly")


@router.message(Command("screenshot"))
async def screenshot_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    try:
        url = validate_url(parse_single_url_arg(command.args))
        job = create_background_job(message, "screenshot", url)
        await message.answer(f"Job ID: {job.id}\nStatus: {job.status}")
        task = asyncio.create_task(run_screenshot_job(job, message))
        job_store.register_task(job.id, task)
    except CommandArgumentError:
        await message.answer(url_usage("screenshot"))
    except (URLValidationError, JobLimitError) as exc:
        await message.answer(f"Error: {exc}")


async def run_screenshot_job(job: Job, message: Message) -> None:
    settings = get_settings()
    job_store.update_job(job.id, status="running", progress=10)
    try:
        options = ScreenshotOptions(
            timeout_seconds=settings.browser_timeout_seconds,
            viewport_width=settings.screenshot_viewport_width,
            viewport_height=settings.screenshot_viewport_height,
            max_size_mb=settings.max_screenshot_size_mb,
            minimum_free_mb=settings.min_free_disk_mb,
            cookies=browser_cookies_for_job(job),
        )
        result = await capture_screenshot(
            job.url, Path(settings.downloads_dir), options
        )
        job_store.update_job(job.id, progress=90)
        await message.answer_document(
            FSInputFile(result.path),
            caption=(
                f"Filename: {result.filename}\n"
                f"Size: {result.size_bytes} bytes\n"
                f"Final URL: {result.final_url}"
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
            result_message=f"Screenshot captured and sent: {result.filename}",
        )
    except asyncio.CancelledError:
        if (current := job_store.get_job(job.id)) and current.status != "cancelled":
            job_store.update_job(job.id, status="cancelled")
        raise
    except NotImplementedError as exc:
        safe_message = map_browser_runtime_error(exc) or "Browser request failed"
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
        safe_message = "Telegram could not send the screenshot file"
        log_safe_job_error(job, exc, safe_message)
        await fail_job(job.id, message, safe_message)
    except Exception as exc:
        safe_message = "Browser request failed"
        log_safe_job_error(job, exc, safe_message)
        await fail_job(job.id, message, safe_message)


@router.message(Command("pdf"))
async def pdf_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    try:
        url = validate_url(parse_single_url_arg(command.args))
        job = create_background_job(message, "pdf", url)
        await message.answer(f"Job ID: {job.id}\nStatus: {job.status}")
        task = asyncio.create_task(run_pdf_job(job, message))
        job_store.register_task(job.id, task)
    except CommandArgumentError:
        await message.answer(url_usage("pdf"))
    except (URLValidationError, JobLimitError) as exc:
        await message.answer(f"Error: {exc}")


async def run_pdf_job(job: Job, message: Message) -> None:
    settings = get_settings()
    job_store.update_job(job.id, status="running", progress=10)
    try:
        options = PdfOptions(
            timeout_seconds=settings.browser_timeout_seconds,
            format=settings.pdf_format,
            print_background=settings.pdf_print_background,
            max_size_mb=settings.max_pdf_size_mb,
            minimum_free_mb=settings.min_free_disk_mb,
            cookies=browser_cookies_for_job(job),
        )
        result = await export_pdf(job.url, Path(settings.downloads_dir), options)
        job_store.update_job(job.id, progress=90)
        await message.answer_document(
            FSInputFile(result.path),
            caption=(
                f"Filename: {result.filename}\n"
                f"Size: {result.size_bytes} bytes\n"
                f"Final URL: {result.final_url}"
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
            result_message=f"PDF exported and sent: {result.filename}",
        )
    except asyncio.CancelledError:
        if (current := job_store.get_job(job.id)) and current.status != "cancelled":
            job_store.update_job(job.id, status="cancelled")
        raise
    except NotImplementedError as exc:
        safe_message = map_browser_runtime_error(exc) or "Browser request failed"
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
        safe_message = "Telegram could not send the PDF file"
        log_safe_job_error(job, exc, safe_message)
        await fail_job(job.id, message, safe_message)
    except Exception as exc:
        safe_message = "Browser request failed"
        log_safe_job_error(job, exc, safe_message)
        await fail_job(job.id, message, safe_message)


async def fail_job(job_id: str, message: Message, error: str) -> None:
    job_store.update_job(job_id, status="failed", error_message=error)
    await message.answer(f"Job {job_id} failed: {error}")


def log_safe_job_error(job: Job, error: BaseException, safe_message: str) -> None:
    logger.warning(
        "Background job failed: job_id=%s command=%s exception_type=%s safe_message=%s",
        job.id,
        job.command,
        type(error).__name__,
        safe_message,
    )


def format_job(job: Job) -> str:
    details = [
        f"Job ID: {job.id}",
        f"Command: /{job.command}",
        f"Status: {job.status}",
        f"Progress: {job.progress}%",
    ]
    if job.result_message:
        details.append(f"Result: {job.result_message}")
    if job.error_message:
        details.append(f"Error: {job.error_message}")
    return "\n".join(details)


@router.message(Command("status"))
async def status_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    if not command.args:
        await message.answer("Usage: /status <job_id>")
        return
    user_id = get_user_id(message)
    job = job_store.get_job(command.args.strip())
    if job is None or user_id is None or (job.user_id != user_id and not is_admin(user_id)):
        await message.answer("Job not found.")
        return
    await message.answer(format_job(job))


@router.message(Command("jobs"))
async def jobs_handler(message: Message) -> None:
    if await reject_unless_allowed(message):
        return
    user_id = get_user_id(message)
    if user_id is None:
        await message.answer("No jobs found.")
        return
    jobs = job_store.list_jobs() if is_admin(user_id) else job_store.list_user_jobs(user_id)
    if not jobs:
        await message.answer("No jobs found.")
        return
    await message.answer("\n\n".join(format_job(job) for job in jobs[:10]))


@router.message(Command("cancel"))
async def cancel_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    if not command.args:
        await message.answer("Usage: /cancel <job_id>")
        return
    user_id = get_user_id(message)
    if user_id is None or not job_store.cancel_job(
        command.args.strip(), user_id, is_admin(user_id)
    ):
        await message.answer("Job not found, not active, or not owned by you.")
        return
    await message.answer(f"Job {command.args.strip()} cancelled.")


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
            await message.answer("Cookie import is disabled.")
            return
        if not settings.cookie_encryption_key:
            pending_cookie_imports.pop(user_id, None)
            await message.answer(
                "Cookie encryption key is not configured. Ask the bot owner to configure it."
            )
            return
        try:
            cookies = validate_cookies_json(
                message.text, domain, settings.max_cookie_import_size_kb
            )
            save_cookies(user_id, domain, json.dumps(cookies, separators=(",", ":")))
        except (CookieValidationError, EncryptionError, OSError) as exc:
            await message.answer(f"Error: {exc}")
            return

        pending_cookie_imports.pop(user_id, None)
        await message.answer(f"Cookies saved for {domain}")
        return

    stripped = message.text.strip()
    if not stripped.lower().startswith(("http://", "https://")):
        return
    language = get_language(user_id)
    if not is_allowed_user(user_id):
        await message.answer(text("access_denied", language))
        return
    url = detect_plain_url(message.text)
    if url is None:
        await message.answer(text("invalid_url", language))
        return
    await create_url_card(message, user_id, url)
