import asyncio
from pathlib import Path

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import Command, CommandObject
from aiogram.types import FSInputFile, Message

from app.config import get_settings, parse_telegram_ids
from app.core.access_control import is_admin, is_allowed_user
from app.core.download_quota import download_quota
from app.core.jobs import Job, JobLimitError, job_store
from app.core.storage import StorageError
from app.core.url_validation import URLValidationError, validate_url
from app.fetchers.http_fetcher import FetchError, HttpFetcher
from app.fetchers.file_downloader import DownloadError, FileDownloader
from app.fetchers.html_export import save_html
from app.fetchers.link_extractor import LinkExtractor

router = Router()

HELP_TEXT = (
    "Commands:\n"
    "/fetch <url> - fetch a web page\n"
    "/links <url> - list links from a web page\n"
    "/html <url> - export page HTML\n"
    "/download <url> - download a direct file link\n"
    "/status <job_id> - show job status\n"
    "/jobs - list recent jobs\n"
    "/cancel <job_id> - cancel an active job\n"
    "/whoami - show your Telegram ID\n"
    "/help - show this help"
)

ACCESS_DENIED = "Access denied. Ask the bot owner for access."


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
        await message.answer(ACCESS_DENIED)
        return
    settings = get_settings()
    admins = sorted(parse_telegram_ids(settings.admin_telegram_ids))
    allowed = sorted(parse_telegram_ids(settings.allowed_telegram_ids))
    allowed_text = ", ".join(map(str, allowed)) if allowed else "admins only"
    await message.answer(
        f"Admins: {', '.join(map(str, admins)) or 'none'}\nAllowed users: {allowed_text}"
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
        body = response.text[:3500]
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
        links = LinkExtractor.extract(response.text, str(response.url))
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


async def fail_job(job_id: str, message: Message, error: str) -> None:
    job_store.update_job(job_id, status="failed", error_message=error)
    await message.answer(f"Job {job_id} failed: {error}")


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
