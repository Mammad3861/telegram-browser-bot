import asyncio
import json
import logging
from pathlib import Path
from urllib.parse import urlparse

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile, Message

from app.config import get_settings, parse_telegram_ids
from app.core.access_control import deny_runtime_user, is_admin, is_allowed_user
from app.core.access_store import (
    add_allowed_user,
    list_allowed_users,
)
from app.core.download_quota import download_quota
from app.core.cookies import CookieValidationError, normalize_domain, validate_cookies_json
from app.core.encryption import EncryptionError
from app.core.jobs import Job, JobLimitError, job_store
from app.core.session_store import (
    delete_session,
    list_sessions,
    load_cookies_for_domain,
    save_cookies,
)
from app.core.storage import StorageError
from app.core.url_validation import URLValidationError, validate_url
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
from app.fetchers.file_downloader import DownloadError, FileDownloader
from app.fetchers.html_export import save_html
from app.fetchers.link_extractor import LinkExtractor

router = Router()
logger = logging.getLogger(__name__)

HELP_TEXT = (
    "Commands:\n"
    "/fetch <url> - fetch a web page\n"
    "/links <url> - list links from a web page\n"
    "/html <url> - export page HTML\n"
    "/html_rendered <url> - export browser-rendered HTML\n"
    "/download <url> - download a direct file link\n"
    "/screenshot <url> - capture a full-page PNG\n"
    "/pdf <url> - export a page as PDF\n"
    "/cookies_help - show cookie import help\n"
    "/cookies_import <domain> - import cookies\n"
    "/sessions - list your saved sessions\n"
    "/delete_session <domain> - delete a saved session\n"
    "/allow <telegram_id> [note] - grant runtime access\n"
    "/deny <telegram_id> - revoke runtime access\n"
    "/allowed_users - list configured users\n"
    "/status <job_id> - show job status\n"
    "/jobs - list recent jobs\n"
    "/cancel <job_id> - cancel an active job\n"
    "/whoami - show your Telegram ID\n"
    "/help - show this help"
)

ACCESS_DENIED = "Access denied. Ask the bot owner for access."
ADMIN_REQUIRED = "Admin access required."
pending_cookie_imports: dict[int, str] = {}


def get_user_id(message: Message) -> int | None:
    return message.from_user.id if message.from_user else None


async def reject_unless_allowed(message: Message) -> bool:
    user_id = get_user_id(message)
    if user_id is None or not is_allowed_user(user_id):
        await message.answer(ACCESS_DENIED)
        return True
    return False


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    await message.answer("Telegram Browser Bot is ready.\n\n" + HELP_TEXT)


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    await message.answer(HELP_TEXT)


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
    if not command.args:
        await message.answer("Usage: /fetch <url>")
        return

    try:
        async with HttpFetcher() as fetcher:
            response = await fetcher.fetch(command.args.strip())
        body = safe_response_text(response)[:3500]
        await message.answer(f"Status: {response.status_code}\n\n{body}")
    except (URLValidationError, FetchError) as exc:
        await message.answer(f"Error: {exc}")


@router.message(Command("links"))
async def links_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    if not command.args:
        await message.answer("Usage: /links <url>")
        return

    try:
        url = command.args.strip()
        async with HttpFetcher() as fetcher:
            response = await fetcher.fetch(url)
        links = LinkExtractor.extract(safe_response_text(response), str(response.url))
        if not links:
            await message.answer("No links found.")
            return
        text = "\n".join(links[:50])
        await message.answer(text[:4000])
    except (URLValidationError, FetchError) as exc:
        await message.answer(f"Error: {exc}")


@router.message(Command("html"))
async def html_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    if not command.args:
        await message.answer("Usage: /html <url>")
        return

    try:
        url = validate_url(command.args.strip())
        job = create_background_job(message, "html", url)
        await message.answer(f"Job ID: {job.id}\nStatus: {job.status}")
        task = asyncio.create_task(run_html_job(job, message))
        job_store.register_task(job.id, task)
    except (URLValidationError, JobLimitError) as exc:
        await message.answer(f"Error: {exc}")


def create_background_job(message: Message, command: str, url: str) -> Job:
    user_id = get_user_id(message)
    if user_id is None:
        raise JobLimitError("Unable to identify the requesting user.")
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
    if not command.args:
        await message.answer("Usage: /html_rendered <url>")
        return

    try:
        url = validate_url(command.args.strip())
        job = create_background_job(message, "html_rendered", url)
        await message.answer(f"Job ID: {job.id}\nStatus: {job.status}")
        task = asyncio.create_task(run_rendered_html_job(job, message))
        job_store.register_task(job.id, task)
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
    except (
        URLValidationError,
        RenderedHtmlBrowserNotInstalledError,
        RenderedHtmlTimeoutError,
        RenderedHtmlError,
        EncryptionError,
        StorageError,
        OSError,
    ) as exc:
        log_safe_job_error(exc, str(exc))
        await fail_job(job.id, message, str(exc))
    except TelegramAPIError as exc:
        safe_message = "Telegram could not send the rendered HTML file"
        log_safe_job_error(exc, safe_message)
        await fail_job(job.id, message, safe_message)
    except Exception as exc:
        safe_message = "Rendered HTML job failed unexpectedly"
        log_safe_job_error(exc, safe_message)
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
    if not command.args:
        await message.answer("Usage: /download <url>")
        return

    user_id = get_user_id(message)
    settings = get_settings()
    if user_id is None or download_quota.remaining(
        user_id, settings.max_downloads_per_user_per_day
    ) <= 0:
        await message.answer("Daily download quota exceeded. Try again tomorrow.")
        return

    try:
        url = validate_url(command.args.strip())
        job = create_background_job(message, "download", url)
        download_quota.consume(user_id, settings.max_downloads_per_user_per_day)
        await message.answer(f"Job ID: {job.id}\nStatus: {job.status}")
        task = asyncio.create_task(run_download_job(job, message))
        job_store.register_task(job.id, task)
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
            result_message = f"File downloaded and sent: {result.filename}"
        job_store.update_job(
            job.id, status="success", progress=100, result_message=result_message
        )
    except asyncio.CancelledError:
        if (current := job_store.get_job(job.id)) and current.status != "cancelled":
            job_store.update_job(job.id, status="cancelled")
        raise
    except TelegramAPIError:
        message_text = "Telegram could not accept the upload. The file remains saved locally."
        job_store.update_job(
            job.id, status="success", progress=100, result_message=message_text
        )
        await message.answer(message_text)
    except (URLValidationError, DownloadError, StorageError, OSError) as exc:
        await fail_job(job.id, message, str(exc))
    except Exception:
        await fail_job(job.id, message, "Job failed unexpectedly")


@router.message(Command("screenshot"))
async def screenshot_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    if not command.args:
        await message.answer("Usage: /screenshot <url>")
        return

    try:
        url = validate_url(command.args.strip())
        job = create_background_job(message, "screenshot", url)
        await message.answer(f"Job ID: {job.id}\nStatus: {job.status}")
        task = asyncio.create_task(run_screenshot_job(job, message))
        job_store.register_task(job.id, task)
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
        log_safe_job_error(exc, str(exc))
        await fail_job(job.id, message, str(exc))
    except TelegramAPIError as exc:
        safe_message = "Telegram could not send the screenshot file"
        log_safe_job_error(exc, safe_message)
        await fail_job(job.id, message, safe_message)
    except Exception as exc:
        safe_message = "Screenshot job failed unexpectedly"
        log_safe_job_error(exc, safe_message)
        await fail_job(job.id, message, safe_message)


@router.message(Command("pdf"))
async def pdf_handler(message: Message, command: CommandObject) -> None:
    if await reject_unless_allowed(message):
        return
    if not command.args:
        await message.answer("Usage: /pdf <url>")
        return

    try:
        url = validate_url(command.args.strip())
        job = create_background_job(message, "pdf", url)
        await message.answer(f"Job ID: {job.id}\nStatus: {job.status}")
        task = asyncio.create_task(run_pdf_job(job, message))
        job_store.register_task(job.id, task)
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
        log_safe_job_error(exc, str(exc))
        await fail_job(job.id, message, str(exc))
    except TelegramAPIError as exc:
        safe_message = "Telegram could not send the PDF file"
        log_safe_job_error(exc, safe_message)
        await fail_job(job.id, message, safe_message)
    except Exception as exc:
        safe_message = "PDF job failed unexpectedly"
        log_safe_job_error(exc, safe_message)
        await fail_job(job.id, message, safe_message)


async def fail_job(job_id: str, message: Message, error: str) -> None:
    job_store.update_job(job_id, status="failed", error_message=error)
    await message.answer(f"Job {job_id} failed: {error}")


def log_safe_job_error(error: BaseException, safe_message: str) -> None:
    logger.warning(
        "Background job failed: exception_type=%s safe_message=%s",
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
async def pending_cookie_import_handler(message: Message) -> None:
    user_id = get_user_id(message)
    if user_id is None or user_id not in pending_cookie_imports or not message.text:
        return
    if not is_allowed_user(user_id):
        pending_cookie_imports.pop(user_id, None)
        await message.answer(ACCESS_DENIED)
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
