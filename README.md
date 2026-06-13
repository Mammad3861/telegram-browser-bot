# Telegram Browser Bot

[![CI](https://github.com/mammad3861/telegram-browser-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/mammad3861/telegram-browser-bot/actions/workflows/ci.yml)

> v1.1 alpha. This project is ready for controlled early testing, not unrestricted public deployment.

A Telegram bot for fetching web pages, extracting links, exporting browser artifacts, downloading direct files, and using encrypted per-user browser sessions.

## Version

v1.2.0-alpha.1

## Features

- Telegram bot commands include browser exports, downloads, jobs, and encrypted cookie session management.
- Interactive Telegram menu and URL action cards with inline buttons
- Native Telegram Menu button command registration with English/Persian descriptions
- Basic DuckDuckGo HTML web search with interactive result cards
- Basic in-memory English/Persian language preferences
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
- Docker-first Ubuntu 24.04 deployment
- Test coverage

## Target Runtime

The officially supported deployment runtime is Linux/Ubuntu or Docker. For production, prefer an Ubuntu server or a Docker image with the required Playwright Chromium dependencies.

Windows local development is best-effort. Async Playwright behavior, VPN networking, and browser subprocess handling may differ on Windows. The application does not install or configure a Windows-specific asyncio event loop policy.

Install Chromium after installing project dependencies:

```bash
python -m playwright install chromium
```

## Setup

Linux/Ubuntu:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
cp .env.example .env
python -m playwright install chromium
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Windows best-effort local development:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
python -m playwright install chromium
python -m uvicorn app.main:app --reload
```

Playwright installs with the project, but Chromium must be installed separately with the command above. The application never downloads browsers automatically at runtime.

Set `TELEGRAM_BOT_TOKEN` and at least one ID in `ADMIN_TELEGRAM_IDS` inside `.env` before starting the application.

The API health check is available at `http://127.0.0.1:8000/health`. Telegram polling starts automatically when a token is configured.

## Commands

- `/start` - start the bot and show commands
- `/menu` - open the interactive Telegram menu
- `/search <query>` - search the web and open results as URL cards
- `/language [en|fa]` - view or change your language preference
- `/about` - show project version and supported runtime
- `/help` - show short, friendly command help
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
- `/admin_status` - show safe application and storage diagnostics (admin only)
- `/cleanup` - delete generated files older than the configured retention period (admin only)
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

`/start`, `/menu`, `/help`, `/language`, `/about`, and `/whoami` are public. Browser, download, job, and cookie/session commands require an admin or allowed user. `/allow`, `/deny`, `/allowed_users`, and `/access` are admin-only. Admins always retain access.

Static access is configured through environment variables. Runtime access changes are persisted locally without restarting the bot.

## Runtime Access

Static allowed users come from `ALLOWED_TELEGRAM_IDS`. Runtime users are stored in `ACCESS_STORAGE_PATH`, which defaults to `downloads/access/allowed_users.json`. Both sources are combined by access checks; if both are empty, only admins may use protected commands.

```env
ACCESS_STORAGE_PATH=downloads/access/allowed_users.json
ENABLE_RUNTIME_ACCESS_MANAGEMENT=true
CLEANUP_MAX_AGE_HOURS=24
DELETE_GENERATED_FILES_AFTER_SEND=true
URL_SESSION_TTL_MINUTES=60
REGISTER_BOT_COMMANDS=true
SEARCH_PROVIDER=duckduckgo_html
SEARCH_RESULTS_LIMIT=5
SEARCH_TIMEOUT_SECONDS=15
SEARCH_QUERY_MAX_LENGTH=200
SEARCH_SESSION_TTL_MINUTES=30
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
CLEANUP_MAX_AGE_HOURS=24
DELETE_GENERATED_FILES_AFTER_SEND=true
URL_SESSION_TTL_MINUTES=60
REGISTER_BOT_COMMANDS=true
SEARCH_PROVIDER=duckduckgo_html
SEARCH_RESULTS_LIMIT=5
SEARCH_TIMEOUT_SECONDS=15
SEARCH_QUERY_MAX_LENGTH=200
SEARCH_SESSION_TTL_MINUTES=30
```

Direct downloads are streamed into `DOWNLOADS_DIR/files` and never loaded fully into RAM. The declared `Content-Length` and actual streamed byte count are both checked against `MAX_DOWNLOAD_SIZE_MB`. Files above `TELEGRAM_MAX_UPLOAD_SIZE_MB` remain saved locally and are not uploaded to Telegram.

Direct downloads support direct file URLs only. They do not scrape HTML pages to discover download links. The per-user daily quota is stored in memory and resets when the bot process restarts.

`/cleanup` removes files older than `CLEANUP_MAX_AGE_HOURS` only from `html`, `html_rendered`, `files`, `screenshots`, and `pdf`. It never removes runtime access data or encrypted sessions.

Generated files are deleted automatically after a successful Telegram upload by default. Persistent data under `downloads/sessions` and `downloads/access` is never removed by this behavior. Set `DELETE_GENERATED_FILES_AFTER_SEND=false` to retain generated output for debugging. Administrators can still run `/cleanup` to remove old leftovers.

## Interactive URL Cards

Allowed users can send a single public `http://` or `https://` URL as a plain message. The bot validates it and returns an action card without fetching the page automatically. Inline buttons provide Screenshot, PDF, HTML, Rendered HTML, Links, Download, Refresh, and Cancel actions.

URL cards use short in-memory session IDs rather than full URLs in callback data. Sessions belong to their creator, expire after `URL_SESSION_TTL_MINUTES`, and reset when the process restarts. Refresh extends the card lifetime without fetching the URL.

`/language en` and `/language fa` select the English or Persian interface. Persian support is currently basic and focuses on the menu, help, URL cards, and common messages. Language preferences are in memory and reset on restart.

## Telegram Menu Button

When the bot starts with a configured token, it registers a concise native Telegram command menu containing `/start`, `/menu`, `/search`, `/help`, `/language`, `/about`, `/sessions`, and `/whoami`. Persian command descriptions are registered for Telegram clients using the `fa` language code.

Configured administrators receive a chat-scoped menu that also includes `/admin_status`, `/allowed_users`, `/allow`, `/deny`, and `/cleanup`. Advanced browser slash commands remain available without cluttering the native Menu button.

Set `REGISTER_BOT_COMMANDS=false` to skip command registration. Registration errors are logged as warnings and do not prevent bot polling from starting.

## Web Search

`/search <query>` performs a basic alpha web search using `SEARCH_PROVIDER`, currently `duckduckgo_html`. Search is also available from the interactive menu and Telegram's native Menu button.

Results appear in an inline card. Selecting a numbered result validates its URL and opens the existing URL action card. Invalid, localhost, private-IP, file, and script URLs are discarded before the search session is stored.

Search sessions are owner-bound, in memory, expire after `SEARCH_SESSION_TTL_MINUTES`, and reset when the bot restarts. Provider failures return a generic safe error. The project does not scrape Google or bypass search-engine anti-bot systems. Set `SEARCH_PROVIDER=disabled` to disable provider-backed search.

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

```bash
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
- Some content requires login or an existing session. Encrypted imported cookies can support compatible browser sessions, but interactive login is not implemented.
- VPN, proxy, firewall, DNS, or other network restrictions can cause connection errors.
- If HTTP decoding fails, try `/html_rendered`, `/screenshot`, or the supported Linux/Docker environment.
- Windows local browser automation is best-effort. If browser jobs fail with asyncio subprocess errors, test on Ubuntu or Docker.

## Docker Compose Deployment

Docker Compose on Ubuntu 24.04 is the preferred deployment path. The image installs Python 3.12 dependencies, Playwright system packages, and Chromium during the build. Browser installation never happens at application runtime.

Create the environment file and configure at least `TELEGRAM_BOT_TOKEN` and `ADMIN_TELEGRAM_IDS`:

```bash
cp .env.example .env
```

Generate a Fernet key for encrypted cookie sessions, then place the output in `.env` as `COOKIE_ENCRYPTION_KEY`:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Prepare the persistent bind mount for the non-root container user and start the service:

```bash
mkdir -p downloads
sudo chown -R 10001:10001 downloads
docker compose up -d --build
```

Follow logs, test health, and stop the service:

```bash
docker compose logs -f
curl http://127.0.0.1:18080/health
docker compose down
```

The `./downloads:/app/downloads` mount persists generated files, runtime access data, and encrypted sessions across container replacement. Do not commit this directory.

Telegram polling makes outbound connections, so ports 80 and 443 do not need to be exposed. Port `8000` is published as `127.0.0.1:18080` only for local health checks. If `TELEGRAM_BOT_TOKEN` is missing, the API and health endpoint still start while polling remains disabled. If `COOKIE_ENCRYPTION_KEY` is missing, cookie import is disabled while other features continue to work.

## Releases

Alpha releases are created automatically when a version tag matching `v*` is pushed. The release workflow runs the test suite before creating the GitHub Release and uses `CHANGELOG.md` for release notes.

```bash
git tag v1.2.0-alpha.1
git push origin v1.2.0-alpha.1
```

GitHub provides the generated source archives. Docker images are validated in CI but are not published.

## Post-v1 Roadmap

- Additional search providers and richer result presentation
- Admin-editable bot texts, descriptions, and help messages
- Per-language editable welcome, help, and about texts
- Persistent user language preferences
- Richer Telegram UI and editable job-status cards


## Project Status

This project is in alpha and suitable for controlled early testing on Ubuntu 24.04 or Docker Compose. Public deployment still requires persistent jobs and quotas, stronger abuse protection, and broader operational testing.

