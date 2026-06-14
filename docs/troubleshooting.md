# Troubleshooting

## Low Disk Space

The bot checks free space before creating output. Increase available disk space or adjust `MIN_FREE_DISK_MB` carefully. Generated files are deleted after successful Telegram upload by default; admins can run `/cleanup` for leftovers.

Persistent `sessions`, `access`, `preferences`, `texts`, `ui_sessions`, and `jobs` stores are intentionally preserved.

## Docker Permission Denied

The container runs as a non-root user. Fix ownership on the bind mount:

```bash
mkdir -p downloads
sudo chown -R 10001:10001 downloads
docker compose restart
```

## Playwright Or Browser Errors

The Docker image installs Chromium during build. Rebuild the image if the browser is missing:

```bash
docker compose build --no-cache
docker compose up -d
```

For non-Docker Linux development:

```bash
python -m playwright install chromium
```

Some sites block headless browsers or require JavaScript, authentication, or CAPTCHA completion. The bot does not bypass these controls.

## Search Unavailable

`duckduckgo_html` is a basic alpha provider and can fail because of upstream changes, rate limits, or network restrictions. Try again later or send a direct URL to use the normal action card. Check `SEARCH_PROVIDER` and container logs.

## Telegram Command Menu Cache

Telegram's native bottom command menu follows the Telegram client's language and the Bot API command `language_code`. It does not follow the language selected with the bot's `/language` command.

English descriptions are registered as the no-language default and Persian descriptions are registered with `language_code="fa"`. For a primarily Persian bot, set `FORCE_PERSIAN_COMMAND_MENU=true` to make Persian descriptions the no-language default as well.

Telegram clients may cache command menu updates. Confirm `REGISTER_BOT_COMMANDS=true`, restart the bot, then reopen the chat or restart the Telegram client. Command registration failures are warnings and do not stop polling.

## HTTP And Network Problems

- HTTP 403 usually means the site blocks automated requests.
- VPN, proxy, DNS, firewall, or regional restrictions can cause connection failures.
- JavaScript-heavy pages may work better with `/html_rendered` or `/screenshot`.
- A decoding error may be avoided by using a Playwright command on the supported Linux/Docker runtime.

## Windows Development

Windows is best-effort only. Async Playwright subprocess behavior and VPN networking may differ from Ubuntu. The application intentionally does not install a Windows-specific event loop policy. Reproduce browser issues on Ubuntu 24.04 or Docker before reporting them.
