# Telegram Browser Bot

> Early development / MVP. This project is currently experimental and not ready for public production use.

A Telegram bot for fetching web pages, extracting links, exporting HTML, and building toward downloads, screenshots, PDFs, and authenticated browser sessions.

## Version

v0.2.0

## Features

- Telegram bot commands: `/start`, `/help`, `/whoami`, `/access`, `/fetch`, `/links`, `/html`
- Secure URL validation
- Basic SSRF protection
- Public/private Telegram command access control
- Admin and allowed user configuration
- Web page fetching with HTTPX
- Link extraction with BeautifulSoup
- HTML export as `.html` or `.html.gz`
- Disk-space check before saving HTML files
- FastAPI health endpoint
- Docker Compose skeleton
- Test coverage

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

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
- `/access` - show access settings (admins only)

## Access Control

Configure comma-separated Telegram user IDs in `.env`:

```env
ADMIN_TELEGRAM_IDS=123456789
ALLOWED_TELEGRAM_IDS=123456789,987654321
```

`/start`, `/help`, and `/whoami` are public. `/fetch`, `/links`, and `/html` require an admin or allowed user. `/access` is admin-only. If `ALLOWED_TELEGRAM_IDS` is empty, only admins can use protected commands.

Access is configured through environment variables in v0.2; database-based user management is not implemented yet.

## Storage Limits

HTML exports are stored under `DOWNLOADS_DIR/html` before being sent. Files larger than `MAX_HTML_SIZE_MB` are sent as `.html.gz`. The bot refuses to save HTML when available disk space is below `MIN_FREE_DISK_MB`.

```env
MAX_HTML_SIZE_MB=5
DOWNLOADS_DIR=downloads
MIN_FREE_DISK_MB=512
```

## Tests

```powershell
python -m pytest
```

## Troubleshooting

- Some sites block automated requests and return HTTP 403.
- Some sites require JavaScript rendering, which is not supported in v0.2.
- Some content requires login or an existing session, which is not supported yet.
- VPN, proxy, firewall, DNS, or other network restrictions can cause connection errors.

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

## Planned Features

- HTML export as `.html` or `.html.gz`
- File download with storage-aware limits
- Admin-only access control
- User allowlist
- Per-user rate limits
- Server disk-space detection
- Docker deployment
- Future support for Cloudflare Worker / Pages compatibility
- Playwright-based screenshots and PDF export


## Project Status

This project is in early development. It is currently suitable for local testing and controlled usage only. Public deployment requires rate limiting, access control, storage limits, and stronger abuse protection.

