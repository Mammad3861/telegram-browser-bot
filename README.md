# Telegram Browser Bot

> Early development / MVP. This project is currently experimental and not ready for public production use.

A Telegram bot for fetching web pages, extracting links, exporting browser artifacts, downloading direct files, and using encrypted per-user browser sessions.

## Version

v0.9.0

## Features

- Telegram bot commands include browser exports, downloads, jobs, and encrypted cookie session management.
- Secure URL validation
- Basic SSRF protection
- Public/private Telegram command access control
- Admin and allowed user configuration
- Web page fetching with HTTPX
- Link extraction with BeautifulSoup
- HTML export as `.html` or `.html.gz`
- Playwright-rendered HTML export after JavaScript execution
- Streaming direct-file downloads with SHA256 metadata
- In-memory background jobs with global and per-user concurrency limits
- Playwright Chromium full-page PNG screenshots
- Playwright Chromium PDF export with background graphics
- Encrypted per-user, per-domain Playwright cookie sessions
- Persistent local runtime allowlist managed by bot administrators
- Disk-space checks before saving HTML, downloads, screenshots, and PDFs
- FastAPI health endpoint
- Docker Compose skeleton
- Test coverage

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
python -m playwright install chromium
```

Playwright installs with the project, but Chromium must be installed separately with the command above. The application never downloads browsers automatically at runtime.

Set `TELEGRAM_BOT_TOKEN` and at least one ID in `ADMIN_TELEGRAM_IDS` inside `.env`, then run:

```powershell
python -m uvicorn app.main:app --reload
```

The API health check is available at `http://127.0.0.1:8000/health`. Telegram polling starts automatically when a token is configured.

## Commands

- `/start` - start the bot and show commands
- `/help` - show command help
- `/whoami` - show your Telegram user ID
- `/fetch <url>` - fetch and display a web page
- `/links <url>` - extract links from a web page
- `/html <url>` - save and send page HTML
- `/html_rendered <url>` - save browser-rendered HTML after JavaScript execution
- `/rendered_html <url>` - alias for `/html_rendered`
- `/download <url>` - download and send a direct file URL
- `/screenshot <url>` - capture and send a full-page PNG screenshot
- `/pdf <url>` - export and send a page as PDF
- `/cookies_help` - show the accepted cookie import flow
- `/cookies_import <domain>` - import a Playwright-compatible JSON cookie list
- `/sessions` - list your saved session domains
- `/delete_session <domain>` - delete one of your sessions
- `/allow <telegram_id> [note]` - grant runtime access (admin only)
- `/deny <telegram_id>` - revoke runtime access (admin only)
- `/allowed_users` - list static and runtime allowed users (admin only)
- `/status <job_id>` - show progress and result for a job
- `/jobs` - list recent jobs (admins see all jobs)
- `/cancel <job_id>` - cancel an active job
- `/access` - show access settings (admins only)

## Access Control

Configure comma-separated Telegram user IDs in `.env`:

```env
ADMIN_TELEGRAM_IDS=123456789
ALLOWED_TELEGRAM_IDS=123456789,987654321
```

`/start`, `/help`, and `/whoami` are public. Browser, download, job, and cookie/session commands require an admin or allowed user. `/allow`, `/deny`, `/allowed_users`, and `/access` are admin-only. Admins always retain access.

Static access is configured through environment variables. Runtime access changes are persisted locally without restarting the bot.

## Runtime Access

Static allowed users come from `ALLOWED_TELEGRAM_IDS`. Runtime users are stored in `ACCESS_STORAGE_PATH`, which defaults to `downloads/access/allowed_users.json`. Both sources are combined by access checks; if both are empty, only admins may use protected commands.

```env
ACCESS_STORAGE_PATH=downloads/access/allowed_users.json
ENABLE_RUNTIME_ACCESS_MANAGEMENT=true
```

Set `ENABLE_RUNTIME_ACCESS_MANAGEMENT=false` to disable `/allow`, `/deny`, and `/allowed_users`. Existing administrators cannot be removed with `/deny`. The `downloads/access` directory may contain real Telegram user IDs and must not be committed; the project ignores the entire `downloads/` directory.

## Storage Limits

HTTP HTML exports are stored under `DOWNLOADS_DIR/html`, rendered HTML under `DOWNLOADS_DIR/html_rendered`, screenshots under `DOWNLOADS_DIR/screenshots`, and PDFs under `DOWNLOADS_DIR/pdf`. HTML files larger than `MAX_HTML_SIZE_MB` are sent as `.html.gz`. The bot refuses to save output when available disk space is below `MIN_FREE_DISK_MB`.

```env
MAX_HTML_SIZE_MB=5
DOWNLOADS_DIR=downloads
MIN_FREE_DISK_MB=512
MAX_DOWNLOAD_SIZE_MB=50
TELEGRAM_MAX_UPLOAD_SIZE_MB=50
MAX_DOWNLOADS_PER_USER_PER_DAY=10
MAX_CONCURRENT_JOBS_GLOBAL=3
MAX_CONCURRENT_JOBS_PER_USER=1
BROWSER_TIMEOUT_SECONDS=45
SCREENSHOT_VIEWPORT_WIDTH=1366
SCREENSHOT_VIEWPORT_HEIGHT=768
MAX_SCREENSHOT_SIZE_MB=20
MAX_PDF_SIZE_MB=30
PDF_FORMAT=A4
PDF_PRINT_BACKGROUND=true
RENDERED_HTML_WAIT_UNTIL=domcontentloaded
COOKIE_ENCRYPTION_KEY=
SESSION_STORAGE_DIR=downloads/sessions
ENABLE_COOKIE_IMPORT=true
MAX_COOKIE_IMPORT_SIZE_KB=256
ACCESS_STORAGE_PATH=downloads/access/allowed_users.json
ENABLE_RUNTIME_ACCESS_MANAGEMENT=true
```

Direct downloads are streamed into `DOWNLOADS_DIR/files` and never loaded fully into RAM. The declared `Content-Length` and actual streamed byte count are both checked against `MAX_DOWNLOAD_SIZE_MB`. Files above `TELEGRAM_MAX_UPLOAD_SIZE_MB` remain saved locally and are not uploaded to Telegram.

v0.9 supports direct file URLs only. It does not scrape HTML pages to discover download links. The per-user daily quota is stored in memory and resets when the bot process restarts.

## Background Jobs

`/html`, `/html_rendered`, `/download`, `/screenshot`, and `/pdf` run as background jobs. The bot immediately returns a short job ID, and `/status`, `/jobs`, and `/cancel` can be used to manage the work. Users can only view and cancel their own jobs; admins can manage any job.

Jobs are stored in memory in v0.9 and reset whenever the bot process restarts. Redis, Celery, and database persistence are not included yet.

## Cookie Sessions

Generate a Fernet key and place it in `.env` as `COOKIE_ENCRYPTION_KEY`:

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

The key is never generated or persisted automatically. Cookie import is unavailable when the key is missing or when `ENABLE_COOKIE_IMPORT=false`.

Run `/cookies_import example.com`, then send a JSON list in Playwright cookie format:

```json
[
  {
    "name": "session",
    "value": "cookie-value",
    "domain": ".example.com",
    "path": "/"
  }
]
```

Never import cookies from an untrusted source. Cookie values are not echoed by the bot and are stored in encrypted local files under `SESSION_STORAGE_DIR/<user_id>/`. Sessions are isolated by Telegram user and domain, and are used only by `/html_rendered`, `/screenshot`, and `/pdf`. HTTPX commands do not use saved cookies.

## HTML Modes

- `/html <url>` uses a fast HTTP request and returns the server-provided HTML without running JavaScript.
- `/html_rendered <url>` launches Playwright Chromium, runs page JavaScript until the configured load state, and exports the final DOM HTML.

Rendered HTML requires Chromium:

```powershell
python -m playwright install chromium
```

## Tests

```powershell
python -m pytest
```

## Troubleshooting

- Some sites block automated requests and return HTTP 403.
- Some sites block or challenge headless browsers. This project does not bypass CAPTCHAs or anti-bot systems.
- JavaScript-heavy sites may work better with `/html_rendered` or `/screenshot` than `/fetch` or `/html`.
- PDF export may not preserve every animation, lazy-loaded element, or other dynamic page feature perfectly.
- Some content requires login or an existing session, which is not supported yet.
- VPN, proxy, firewall, DNS, or other network restrictions can cause connection errors.

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The current `python:3.12-slim` Compose image does not include Chromium or Playwright system libraries. A production Docker image must install Playwright's Linux dependencies and Chromium explicitly; v0.9 does not automate that setup.

## Planned Features

- Scraping pages for download links
- Docker deployment
- Future support for Cloudflare Worker / Pages compatibility
- Persistent database-backed sessions
- Database-backed access management


## Project Status

This project is in early development. It is currently suitable for local testing and controlled usage only. Public deployment still requires persistent quotas and stronger abuse protection.

