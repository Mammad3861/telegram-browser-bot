# Telegram Browser Bot

[![CI](https://github.com/mammad3861/telegram-browser-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/mammad3861/telegram-browser-bot/actions/workflows/ci.yml)

**Current version:** `v1.9.2-alpha.1`

A Docker-first Telegram bot for safely fetching pages, searching the web, extracting links, downloading direct files, and exporting HTML, screenshots, and PDFs. The supported production target is Ubuntu 24.04 or Docker Compose.

> Alpha software intended for controlled testing. Do not expose it as an unrestricted public service.

## Key Features

- Button-first Telegram browser home, persistent URL tabs, stateful Page options, and provider-labeled search result cards
- HTTP fetch, link extraction, direct and user-confirmed uncertain downloads, HTML, rendered HTML, screenshots, and PDF exports
- English and Persian UI with persistent language preferences
- Static and runtime access control with admin commands
- Administrator-configurable domain/category policy and optional explicit outbound routing
- Persistent URL/search sessions and completed-job history
- Encrypted per-user, per-domain Playwright cookie sessions
- SSRF protection, download limits, disk checks, and automatic temporary-file cleanup
- Docker Compose deployment with localhost-only health, readiness, and liveness endpoints

## Quick Start

```bash
git clone https://github.com/mammad3861/telegram-browser-bot.git
cd telegram-browser-bot
cp .env.example .env
mkdir -p downloads
sudo chown -R 10001:10001 downloads
docker compose up -d --build
```

Minimal `.env`:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_TELEGRAM_IDS=123456789
ALLOWED_TELEGRAM_IDS=
COOKIE_ENCRYPTION_KEY=
```

Check the service:

```bash
docker compose logs -f
curl http://127.0.0.1:18080/health
curl http://127.0.0.1:18080/health/ready
```

## Basic Usage

- Send `/menu` to open the browser home, then tap Search or New URL.
- Send a public `http://` or `https://` URL to open a browser tab card.
- Use the tab buttons for links, screenshots, PDF, HTML, downloads, navigation, and explicit safe interaction.

Advanced slash commands remain available. See the [complete command reference](docs/commands.md).

Admins can use `/admin_status`, `/storage`, and `/cleanup dry_run` for safe beta diagnostics.

## Documentation

- [Docker deployment](docs/deployment-docker.md)
- [Configuration reference](docs/configuration.md)
- [Command reference](docs/commands.md)
- [Web search](docs/search.md)
- [Cookie sessions](docs/cookies.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Roadmap](docs/roadmap.md)
- [Changelog](CHANGELOG.md)

## Security Notes

- URLs are validated and localhost/private network destinations are blocked.
- Search result URLs are validated before URL cards are opened.
- The bot does not bypass CAPTCHAs or anti-bot systems and does not scrape Google directly.
- The bot does not bypass DRM, paywalls, or login restrictions and does not store usernames or passwords.
- Direct downloads support direct file links only. Some sites do not work fully in a headless browser.
- Downloads do not rip streams or bypass DRM, CAPTCHA, paywalls, login restrictions, or anti-bot systems. Use downloads only for files you are authorized to receive.
- Cookie sessions are encrypted locally, isolated by Telegram user and domain, and require a stable encryption key.
- Username/password login storage and OpenAI/ChatGPT assistant features are not implemented.
- Persistent data lives under `downloads/`; do not commit it.

## Roadmap

Near-term work focuses on UX polish, provider-based search improvements, richer session cards, and an optional Telegram Web App prototype. OpenAI assistants, stored username/password login, CAPTCHA bypass, and direct Google scraping are not planned for now.

See the full [roadmap](docs/roadmap.md).

## Development

```bash
python -m pip install -e ".[dev]"
python -m playwright install chromium
python -m pytest
```

Windows development is best-effort. Ubuntu 24.04 or Docker Compose is recommended for browser automation.
