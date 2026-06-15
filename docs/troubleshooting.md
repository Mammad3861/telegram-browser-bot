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

Page interaction is intentionally limited to visible links and simple buttons. It does not fill forms, submit passwords, pass CAPTCHAs, bypass paywalls, or bypass DRM. Some sites therefore cannot work fully inside Telegram or a headless browser.

Page options saves updated URL/title and encrypted Playwright storage state when `COOKIE_ENCRYPTION_KEY` is configured. Without that key, the URL/title still persist but cookies and browser storage are skipped. Some sites may reset state, use unsupported session mechanisms, or block headless browsers, so a consent or confirmation screen can still reappear.

## Direct Download Rejected

Direct Download accepts direct file links only. The bot checks redirects, headers, content type, disposition, and common file extensions. A normal HTML page is rejected even if that page contains links to files.

With `DOWNLOAD_MODE=confirm_unknown`, uncertain links show a confirmation card. `admin_override` additionally gives administrators a force-attempt button, but it never overrides URL safety, content policy, file-size limits, protected streaming blocks, or HTML/stream-manifest rejection. A direct `.mp3` or `.mp4` from a normal permitted file host can work; protected streaming pages cannot.

## Search Unavailable

`duckduckgo_html` is a basic alpha provider and can fail because of upstream changes, rate limits, or network restrictions. Try again later or send a direct URL to use the normal action card. Check `SEARCH_PROVIDER` and container logs.

## Telegram Command Menu Cache

Telegram's native bottom command menu follows the Telegram client's language and the Bot API command `language_code`. It does not follow the language selected with the bot's `/language` command.

In `auto` mode, English descriptions are the no-language default and Persian descriptions use `language_code="fa"`. For a primarily Persian bot, set `COMMAND_MENU_LANGUAGE_MODE=force_fa`, restart, or run `/refresh_commands`. Use `RESET_TELEGRAM_COMMANDS_ON_START=true` once when stale command lists need to be removed before registration.

Telegram clients may cache command menu updates. Confirm `REGISTER_BOT_COMMANDS=true`, restart the bot, then reopen the chat or restart the Telegram client. Command registration failures are warnings and do not stop polling.

## HTTP And Network Problems

- HTTP 403 usually means the site blocks automated requests.
- VPN, proxy, DNS, firewall, or regional restrictions can cause connection failures.
- JavaScript-heavy pages may work better with `/html_rendered` or `/screenshot`.
- A decoding error may be avoided by using a Playwright command on the supported Linux/Docker runtime.

## Windows Development

Windows is best-effort only. Async Playwright subprocess behavior and VPN networking may differ from Ubuntu. The application intentionally does not install a Windows-specific event loop policy. Reproduce browser issues on Ubuntu 24.04 or Docker before reporting them.
