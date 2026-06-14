# Configuration

Configuration is loaded from environment variables and `.env`. Defaults below match `.env.example`.

## Telegram And Access

| Variable | Default | Description |
| --- | --- | --- |
| `TELEGRAM_BOT_TOKEN` | empty | Telegram bot token. Polling stays disabled when missing. |
| `ADMIN_TELEGRAM_IDS` | empty | Comma-separated administrator IDs. |
| `ALLOWED_TELEGRAM_IDS` | empty | Static comma-separated protected-command allowlist. |
| `ACCESS_STORAGE_PATH` | `downloads/access/allowed_users.json` | Runtime allowlist file. |
| `ENABLE_RUNTIME_ACCESS_MANAGEMENT` | `true` | Enables `/allow`, `/deny`, and `/allowed_users`. |
| `REGISTER_BOT_COMMANDS` | `true` | Registers Telegram native command menus at startup. |
| `FORCE_PERSIAN_COMMAND_MENU` | `false` | Uses Persian descriptions for the no-language default command menu. |
| `COMMAND_MENU_LANGUAGE_MODE` | `auto` | Native menu mode: `auto`, `force_fa`, or `force_en`. |
| `RESET_TELEGRAM_COMMANDS_ON_START` | `false` | Deletes old default and Persian command lists before registration. |

Admins always have protected-command access. Static and runtime allowlists are combined. If both are empty, only admins can use protected commands.

Telegram chooses localized native command descriptions using the Telegram client's language and Bot API `language_code`; this is independent of the bot's `/language` preference. For mainly Persian deployments, set `COMMAND_MENU_LANGUAGE_MODE=force_fa`. `FORCE_PERSIAN_COMMAND_MENU` remains as a compatibility setting.

## HTTP And Browser

| Variable | Default | Description |
| --- | --- | --- |
| `REQUEST_TIMEOUT_SECONDS` | `10` | HTTP request timeout. |
| `MAX_RESPONSE_BYTES` | `1000000` | Maximum HTTP response body read by text commands. |
| `BROWSER_TIMEOUT_SECONDS` | `45` | Playwright navigation timeout. |
| `SCREENSHOT_VIEWPORT_WIDTH` | `1366` | Browser viewport width. |
| `SCREENSHOT_VIEWPORT_HEIGHT` | `768` | Browser viewport height. |
| `MAX_SCREENSHOT_SIZE_MB` | `20` | Screenshot output limit. |
| `MAX_PDF_SIZE_MB` | `30` | PDF output limit. |
| `PDF_FORMAT` | `A4` | Playwright PDF paper format. |
| `PDF_PRINT_BACKGROUND` | `true` | Include backgrounds in PDFs. |
| `RENDERED_HTML_WAIT_UNTIL` | `domcontentloaded` | Rendered HTML navigation load state. |
| `INTERACTION_MAX_ELEMENTS` | `10` | Maximum visible links/buttons shown by Interact. |
| `INTERACTION_TIMEOUT_SECONDS` | `30` | Playwright timeout for page interaction. |

## Downloads And Storage

| Variable | Default | Description |
| --- | --- | --- |
| `DOWNLOADS_DIR` | `downloads` | Base directory for persistent and generated data. |
| `MIN_FREE_DISK_MB` | `512` | Required free disk space before output creation. |
| `MAX_HTML_SIZE_MB` | `5` | HTML files above this threshold are gzip compressed. |
| `MAX_DOWNLOAD_SIZE_MB` | `50` | Maximum direct download size. |
| `TELEGRAM_MAX_UPLOAD_SIZE_MB` | `50` | Local Telegram upload threshold. |
| `MAX_DOWNLOADS_PER_USER_PER_DAY` | `10` | In-memory per-user daily direct-download quota. |
| `MAX_CONCURRENT_JOBS_GLOBAL` | `3` | Global active job limit. |
| `MAX_CONCURRENT_JOBS_PER_USER` | `1` | Per-user active job limit. |
| `CLEANUP_MAX_AGE_HOURS` | `24` | Retention used by `/cleanup`. |
| `DELETE_GENERATED_FILES_AFTER_SEND` | `true` | Delete generated files after successful upload. |

Cleanup only targets generated `html`, `html_rendered`, `files`, `screenshots`, and `pdf` directories. Persistent stores are excluded.

## Search

| Variable | Default | Description |
| --- | --- | --- |
| `SEARCH_PROVIDER` | `duckduckgo_html` | `disabled`, `duckduckgo_html`, `brave_api`, or `searxng`. |
| `SEARCH_RESULTS_LIMIT` | `5` | Maximum displayed results. |
| `SEARCH_TIMEOUT_SECONDS` | `15` | Provider request timeout. |
| `BRAVE_SEARCH_API_KEY` | empty | Required when `SEARCH_PROVIDER=brave_api`. |
| `SEARXNG_BASE_URL` | empty | Required when `SEARCH_PROVIDER=searxng`. |
| `SEARCH_QUERY_MAX_LENGTH` | `200` | Maximum query length. |
| `SEARCH_SESSION_TTL_MINUTES` | `30` | Search result card lifetime. |

See [Web Search](search.md) for provider limitations.

## UI Sessions And History

| Variable | Default | Description |
| --- | --- | --- |
| `URL_SESSION_TTL_MINUTES` | `60` | URL action card lifetime. |
| `URL_SESSIONS_PATH` | `downloads/ui_sessions/url_sessions.json` | Persistent URL sessions. |
| `URL_SESSION_MAX_STORED` | `500` | Maximum stored URL sessions. |
| `SEARCH_SESSIONS_PATH` | `downloads/ui_sessions/search_sessions.json` | Persistent search sessions. |
| `SEARCH_SESSION_MAX_STORED` | `300` | Maximum stored search sessions. |
| `JOB_HISTORY_PATH` | `downloads/jobs/job_history.json` | Completed-job summaries. |
| `JOB_HISTORY_MAX_STORED` | `1000` | Maximum completed summaries. |
| `USER_PREFERENCES_PATH` | `downloads/preferences/user_preferences.json` | Persistent user language preferences. |
| `BOT_TEXTS_PATH` | `downloads/texts/bot_texts.json` | Admin-editable bot text overrides. |
| `BOT_TEXT_MAX_LENGTH` | `3000` | Maximum editable text length. |

Active jobs remain in memory. Only safe completed-job summaries are persisted, using URL domains instead of full URLs.

## Content Policy

| Variable | Default | Description |
| --- | --- | --- |
| `CONTENT_POLICY_PATH` | `downloads/policies/content_policy.json` | Atomic local domain/category policy store. |
| `ENABLE_CONTENT_POLICY` | `true` | Enforces policy before cards, fetches, downloads, and browser jobs. |
| `CONTENT_POLICY_DEFAULT_ACTION` | `allow` | Action for domains without a matching rule: `allow` or `block`. |
| `ENABLE_BUILTIN_SAFETY_BLOCKLIST` | `true` | Enables the small built-in adult/gambling seed lists. |
| `BUILTIN_BLOCK_ADULT` | `true` | Enables built-in adult-domain seeds. |
| `BUILTIN_BLOCK_GAMBLING` | `true` | Enables built-in gambling-domain seeds. |

The policy supports explicit blocked/allowed domains, blocked keywords, and lightweight domain lists for media, gambling, adult, and dangerous categories. Explicit allow rules override category rules, but never override URL validation or private/internal destination protection. No external classification service is called.

## Outbound Routing

| Variable | Default | Description |
| --- | --- | --- |
| `ROUTING_PROFILE` | `default` | Fallback route: `default` or `proxy`. |
| `DOMAIN_ROUTE_RULES_PATH` | `downloads/policies/route_rules.json` | Atomic per-domain route rules. |
| `HTTP_PROXY_URL` | empty | Explicit proxy URL for HTTPX HTTP targets. |
| `HTTPS_PROXY_URL` | empty | Explicit proxy URL for HTTPX HTTPS targets. |
| `PLAYWRIGHT_PROXY_SERVER` | empty | Explicit Playwright proxy server URL. |

Only proxy URLs supplied by the administrator are used. The application does not install or manage proxy software, alter system routes, or modify firewall rules. A domain assigned to `proxy` fails safely when the required proxy URL is missing.

## Cookie Sessions

| Variable | Default | Description |
| --- | --- | --- |
| `COOKIE_ENCRYPTION_KEY` | empty | Fernet key used to encrypt imported cookies. |
| `SESSION_STORAGE_DIR` | `downloads/sessions` | Encrypted cookie session directory. |
| `ENABLE_COOKIE_IMPORT` | `true` | Enables cookie import when a key is configured. |
| `MAX_COOKIE_IMPORT_SIZE_KB` | `256` | Maximum cookie JSON payload size. |

Generate a key:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Keep the same key across restarts. Losing it makes existing encrypted sessions unreadable.
