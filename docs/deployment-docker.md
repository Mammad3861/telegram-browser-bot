# Docker Deployment

Ubuntu 24.04 with Docker Compose is the supported production-like deployment target.

## Prerequisites

- Ubuntu 24.04
- Docker Engine with the Compose plugin
- A Telegram bot token from BotFather
- At least one Telegram administrator ID

## Deploy

```bash
git clone https://github.com/mammad3861/telegram-browser-bot.git
cd telegram-browser-bot
cp .env.example .env
```

Edit `.env` and set at least:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
ADMIN_TELEGRAM_IDS=123456789
```

Prepare the persistent bind mount for the container's non-root user:

```bash
mkdir -p downloads
sudo chown -R 10001:10001 downloads
```

Build and start:

```bash
docker compose up -d --build
```

Playwright Chromium and its Linux dependencies are installed while the image is built. Browsers are not installed at application runtime.

## Operations

Follow logs:

```bash
docker compose logs -f
```

Check health:

```bash
curl http://127.0.0.1:18080/health
```

Stop the service:

```bash
docker compose down
```

Telegram polling uses outbound connections, so ports 80 and 443 do not need to be exposed. The health endpoint is bound to localhost at port `18080`.

## Persistent Data

Docker Compose mounts `./downloads:/app/downloads`. Runtime access, encrypted cookies, preferences, editable texts, UI sessions, and completed-job history survive container rebuilds and replacements.

Generated output is deleted after successful Telegram upload by default. Never commit `downloads/` or `.env`.

## Updating

```bash
git pull
docker compose up -d --build
docker compose logs -f
```

The persistent `downloads` mount is retained. Back up `.env` and `downloads/` before major upgrades.

If ownership changes after an update:

```bash
sudo chown -R 10001:10001 downloads
docker compose restart
```
