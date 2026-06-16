# Beta Deployment Checklist

Use this checklist before inviting real users.

## Environment

- Create a Telegram bot token with BotFather.
- Set `TELEGRAM_BOT_TOKEN` in `.env`.
- Set `ADMIN_TELEGRAM_IDS` to at least one Telegram user ID.
- Create and mount the persistent `downloads/` volume.
- Set `COOKIE_ENCRYPTION_KEY` if cookie import is needed.
- Choose `SEARCH_PROVIDER`.
- Choose `DOWNLOAD_MODE`.
- Choose `COMMAND_MENU_LANGUAGE_MODE`.

## Deployment Checks

```bash
docker compose up -d --build
docker compose logs -f
curl http://127.0.0.1:18080/health/ready
```

## Admin Checks

- Run `/setup_check`.
- Run `/admin_status`.
- Run `/storage`.
- Run `/cleanup dry_run`.

## User Flow Checks

- Run `/menu`.
- Send a public URL and confirm a URL card appears.
- Test Screenshot.
- Test PDF.
- Test Download with a direct file URL.
- Test `/search`.
- Test content policy with `/policy_test <url>`.

## Safety Checks

- Confirm `.env` is not committed.
- Confirm `downloads/` is not committed.
- Confirm only trusted admins can use admin commands.
- Confirm the health port is bound to localhost only.
