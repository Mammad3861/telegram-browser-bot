# Telegram Browser Bot

[![CI](https://github.com/mammad3861/telegram-browser-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/mammad3861/telegram-browser-bot/actions/workflows/ci.yml)

**Current version:** `v1.6.0-alpha.1`

A Docker-first Telegram bot for safely fetching pages, searching the web, extracting links, downloading direct files, and exporting HTML, screenshots, and PDFs. The supported production target is Ubuntu 24.04 or Docker Compose.

> Alpha software intended for controlled testing. Do not expose it as an unrestricted public service.

## Key Features

- Interactive Telegram menu, URL action cards, and provider-labeled search result cards
- HTTP fetch, link extraction, direct downloads, HTML, rendered HTML, screenshots, and PDF exports
- English and Persian UI with persistent language preferences
- Static and runtime access control with admin commands
- Administrator-managed domain/category policy and optional explicit outbound routing
- Persistent URL/search sessions and completed-job history
- Encrypted per-user, per-domain Playwright cookie sessions
- SSRF protection, download limits, disk checks, and automatic temporary-file cleanup
- Docker Compose deployment with a localhost-only health endpoint

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
```

## Basic Usage

- Send `/menu` to open the interactive menu.
- Send a public `http://` or `https://` URL to open an action card.
- Send `/search your query` for basic web search results.

Advanced slash commands remain available. See the [complete command reference](docs/commands.md).

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
