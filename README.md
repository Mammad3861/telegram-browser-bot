# Telegram Browser Bot

> Early development / MVP. This project is currently experimental and not ready for public production use.

A Telegram bot for fetching web pages, extracting links, and building toward HTML export, downloads, screenshots, PDFs, and authenticated browser sessions.
# Telegram Browser Bot v0.1.1

A minimal Telegram bot and FastAPI service for fetching public web pages and extracting links.

## Setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Set `TELEGRAM_BOT_TOKEN` in `.env`, then run:

```powershell
python -m uvicorn app.main:app --reload
```

The API health check is available at `http://127.0.0.1:8000/health`. Telegram polling starts automatically when a token is configured.

## Tests

```powershell
python -m pytest
```

## Troubleshooting

- Some sites block automated requests and return HTTP 403.
- Some sites require JavaScript rendering, which is not supported in v0.1.1.
- Some content requires login or an existing session, which is not supported yet.
- VPN, proxy, firewall, DNS, or other network restrictions can cause connection errors.

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```
