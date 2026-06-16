# Changelog

All notable changes to this project are documented in this file.

## [v1.9.2-alpha.1] - 2026-06-16

### Improved

- Persian `/storage` output now shows readable category labels such as `تصویرهای صفحه` and `نشست‌های رابط کاربری`.
- English `/storage` output uses readable labels such as `Screenshots`, `Rendered HTML`, and `UI sessions`.

## [v1.9.1-alpha.1] - 2026-06-16

### Improved

- Telegram-facing admin, storage, cleanup, browser export, and download messages now show human-readable sizes.
- English output uses `B`, `KB`, `MB`, `GB`, and `TB`; Persian output uses `بایت`, `کیلوبایت`, `مگابایت`, `گیگابایت`, and `ترابایت`.
- Readiness health keeps raw byte fields for automation and adds human-readable companion fields.

## [v1.9.0-alpha.1] - 2026-06-16

### Added

- Structured `/health/live` and `/health/ready` endpoints for process and readiness checks.
- Expanded `/admin_status` with uptime, storage, session counts, content policy, search, command menu, download mode, cleanup, and browser diagnostics.
- Admin `/storage` command for category-level downloads usage.
- `/cleanup dry_run` preview mode.
- In-memory rate limits for protected actions, search, and browser jobs.
- Central safe error mapping for common timeout, HTTP, provider, browser, disk, routing, policy, and file-size failures.

### Improved

- Startup validation now falls back safely for invalid search provider, download mode, command menu mode, and content policy default action.
- `/jobs` hides old completed history according to `JOB_RESULT_KEEP_HOURS`.
- Documentation now includes beta-readiness diagnostics, health endpoints, storage checks, cleanup dry runs, and rate-limit settings.

### Safety

- Diagnostics avoid secrets, API keys, cookie values, proxy URLs, and full sensitive URLs.
- No database, Redis, OpenAI/ChatGPT features, media ripping, CAPTCHA bypass, DRM bypass, or paywall bypass was added.

## [v1.8.0-alpha.1] - 2026-06-15

### Added

- Configurable `safe`, `confirm_unknown`, and `admin_override` download modes.
- Owner-bound confirmation cards with metadata, risk acceptance, cancellation, and administrator-only force attempts.
- Find downloads action for selecting file-like links from browser tabs.
- Expanded archive, installer, ebook, image, text, audio, and video direct-file detection.
- Detector reason labels and complete English/Persian download messaging.

### Improved

- HEAD metadata now falls back to streaming GET behavior when unavailable or misleading.
- Confirmed uncertain downloads still reject HTML bodies, streaming manifests, oversized files, unsafe redirects, and protected streaming domains.
- Direct media files from ordinary permitted hosts remain supported within policy and size limits.

### Safety

- No stream ripping, HLS/DASH extraction, DRM/CAPTCHA/paywall bypass, credential storage, or automated bulk downloading was added.

## [v1.7.3-alpha.1] - 2026-06-15

### Fixed

- Renamed the user-facing Interact action to Page options / گزینه‌های صفحه.
- Page-option clicks now capture and persist the resulting URL and page title.
- Encrypted Playwright storage state is saved per user/tab and reused by later Page options, Links, Screenshot, PDF, and Rendered HTML actions.
- Old option lists are invalidated after a successful click and replaced with an updated tab card.
- Added friendly diagnostics when the page updates but encrypted state cannot be saved.

### Safety

- Page options remain user-initiated and limited to visible links and simple buttons.
- No form autofill, password storage, CAPTCHA/DRM/paywall bypass, or automatic age/consent confirmation was added.

## [v1.7.2-alpha.1] - 2026-06-15

### Improved

- Reviewed and rewrote Persian user-facing copy across menus, browser tabs, search, jobs, access, cleanup, uploads, policy, routing, and admin text tools.
- Replaced awkward literal terminology with consistent product language, including `بدون محدودیت` for neutral category state.
- Localized policy decision reasons so internal values such as `default_allow` are never shown to Persian users.
- Expanded Persian `/texts` output with human-readable labels for editable keys and languages.
- Polished Persian Telegram native command descriptions and documentation examples.

### Notes

- No policy, routing, search, access, or browser behavior changed in this wording-only release.

## [v1.7.1-alpha.1] - 2026-06-15

### Added

- Configurable `adult`, `gambling`, `crypto`, `malware`, `phishing`, `dangerous`, `media`, and `custom` policy categories.
- Admin commands for category state and category-domain management.
- Atomic policy schema with allowed categories/keywords and backward migration from legacy category fields.
- English and Persian category names, states, usage messages, and policy summaries.

### Changed

- New policies block only malware, phishing, and dangerous categories by default.
- Built-in adult, gambling, crypto, and media lists now classify domains without automatically blocking them.
- Search result filtering follows the administrator's current category choices.

### Safety

- URL/SSRF validation remains mandatory and cannot be overridden by policy allow rules.
- Protected streaming download guardrails remain separate from media-category permissions.
- No external classification, DRM/CAPTCHA/paywall bypass, media ripping, or credential storage was added.

## [v1.7.0-alpha.1] - 2026-06-15

### Added

- Button-first English/Persian browser home with Search, New URL, Sessions, Recent jobs, Language, and Help.
- Persistent browser-tab history with Back, Refresh, Interact, and existing export/download actions.
- Explicit Playwright interaction for a limited set of visible links and simple buttons.
- Configurable native command-menu language modes and administrator `/refresh_commands`.
- Optional built-in adult and gambling domain seed lists.

### Improved

- Search queries now honor blocked keywords and policy-filtered results.
- Direct downloads use HEAD hints, redirect handling, streaming fallback, and broader direct-file detection.
- Content-policy status, category guidance, Persian messages, and command-menu documentation were polished.

### Safety

- Interaction does not fill forms, submit passwords, bypass age gates automatically, or bypass CAPTCHA, DRM, paywalls, login restrictions, or anti-bot systems.
- Direct download remains limited to direct file links and retains SSRF, policy, storage, and size checks.

## [v1.6.0-alpha.1] - 2026-06-15

### Added

- Atomic local content policy with domain, keyword, and lightweight category rules.
- Admin policy inspection, mutation, testing, and reload commands.
- Optional per-domain `default` or `proxy` outbound routing using explicit admin-provided URLs.
- Admin route listing, mutation, and testing commands.
- Safe media-site card guidance and protected streaming page download guardrails.

### Safety

- Content policy is enforced before URL cards, search-result opening, HTTP actions, downloads, and browser jobs.
- Redirected HTTP and browser destinations retain SSRF and content-policy checks.
- No protected-media extraction, DRM/paywall/CAPTCHA bypass, credential storage, system routing, or firewall changes were added.

## [v1.5.2-alpha.1] - 2026-06-15

### Fixed

- Polished English and Persian descriptions in Telegram's native command menu.
- Verified localized default and per-admin chat command scopes.
- Added `FORCE_PERSIAN_COMMAND_MENU` for Persian-first no-language command menus.
- Documented that Telegram command-menu language is independent from `/language` and may be cached by clients.

## [v1.5.1-alpha.1] - 2026-06-15

### Fixed

- Completed Persian translations across menus, URL/search cards, inline buttons, jobs, access management, admin text commands, cleanup/history responses, cookie sessions, and common errors.
- Preserved Persian button labels when URL and search cards are refreshed through callbacks.
- Localized job status labels and generated-file captions using each user's persisted preference.
- Added strict English/Persian translation-key parity and Persian UI rendering tests.

### Documentation

- Documented broad Persian UI coverage and Telegram client command-menu caching behavior.

## [v1.5.0-alpha.1] - 2026-06-14

### Added

- Registry-backed search providers: `disabled`, `duckduckgo_html`, `brave_api`, and `searxng`.
- Brave Search API integration with secret-safe configuration handling.
- SearxNG JSON API integration with configurable base URL.
- Provider labels and partial-result counts on English and Persian search cards.

### Reliability And Safety

- Hardened DuckDuckGo timeout handling and added a parsing fallback.
- Misconfigured or unavailable providers return safe, friendly messages.
- All provider result URLs continue through the existing URL and SSRF validation.
- No Google scraping, CAPTCHA bypass, OpenAI integration, database, or Redis was added.

## [v1.4.1-alpha.1] - 2026-06-14

### Documentation

- Simplified the README into a concise GitHub landing page and Docker quick start.
- Split deployment, configuration, commands, search, cookies, troubleshooting, and roadmap guidance into dedicated docs.
- Clarified search-provider limitations and safe result URL validation.
- Clarified that OpenAI/ChatGPT features, username/password login storage, CAPTCHA bypass, and direct Google scraping are not planned for now.

### UX

- Improved English and Persian search-unavailable messages with a direct-URL fallback suggestion.

## [v1.4.0-alpha.1] - 2026-06-14

### Added

- Atomic local persistence for owner-bound URL and search UI sessions.
- Safe completed-job history containing URL domains instead of full URLs.
- `/jobs` and `/status` fallback to persisted completed-job summaries after restart.
- Admin-only `/purge_history` command for completed history.
- Configurable storage paths and retention limits for UI sessions and job history.

### Reliability

- Corrupted UI-session or job-history JSON logs a safe warning and falls back to an empty store.
- Cleanup continues to preserve sessions, access, preferences, texts, UI sessions, and job history.
- Active jobs remain in memory; no database or Redis has been added.

## [v1.3.0-alpha.1] - 2026-06-14

### Added

- Atomic JSON persistence for per-user English/Persian language preferences.
- Language-specific editable `welcome`, `help`, and `about` text overrides.
- Admin-only `/texts`, `/set_text`, `/reset_text`, and `/preview_text` commands.
- Configurable preference/text storage paths and editable-text length limit.

### Reliability

- Corrupted preference or text JSON logs a safe warning and falls back to defaults.
- Manual cleanup and post-send cleanup never touch preferences or editable texts.
- Docker's existing `downloads` volume persists both stores across rebuilds and restarts.

## [v1.2.0-alpha.1] - 2026-06-14

### Added

- Protected `/search <query>` command with English and Persian messages.
- DuckDuckGo HTML provider behind a replaceable search-provider abstraction.
- Interactive search result cards with numbered result buttons, refresh, and close actions.
- Owner-bound, expiring in-memory search sessions using compact callback data.
- Safe result URL filtering through existing SSRF validation before opening URL cards.
- Search provider, timeout, result limit, query length, and session TTL settings.

### Safety

- Search failures return a generic safe message without stack traces or query logging.
- Google is not scraped, and no search-engine anti-bot bypass is implemented.

## [v1.1.1-alpha.1] - 2026-06-13

### Added

- Native Telegram Menu button command registration during bot startup.
- Concise default user commands with English and Persian descriptions.
- Per-administrator chat command menus for runtime access and maintenance commands.
- `REGISTER_BOT_COMMANDS` setting, enabled by default.

### Reliability

- Missing bot tokens continue to leave API-only startup available.
- Telegram command registration failures log a safe warning without stopping polling.

## [v1.1.0-alpha.1] - 2026-06-13

### Added

- Interactive `/menu` with Open URL, Sessions, Account, Help, and planned Search actions.
- URL action cards for plain validated URLs with Screenshot, PDF, HTML, Rendered HTML, Links, Download, Refresh, and Cancel buttons.
- Owner-bound in-memory URL sessions with configurable expiration and compact callback data.
- `/language en` and `/language fa` with foundational English/Persian interface translations.
- Shorter localized help text while retaining all advanced slash commands.
- Static localized `/about` command with version and official runtime information.
- Account menu details for Telegram ID, administrator status, access status, and language.

### Notes

- URL sessions and language preferences reset when the bot restarts.
- Web search, persistent language preferences, and admin-editable per-language texts remain planned features.

## [v1.0.1-alpha.1] - 2026-06-13

### Fixed

- Generated HTML, rendered HTML, downloaded files, screenshots, and PDFs are deleted after successful Telegram upload by default.
- Telegram upload failures retain local files for debugging or retry.
- Temporary-file deletion is restricted to generated output folders under `DOWNLOADS_DIR`; encrypted sessions and runtime access data remain protected.

### Added

- `DELETE_GENERATED_FILES_AFTER_SEND` setting, enabled by default.

## [v1.0.0-alpha.1] - 2026-06-13

First alpha release for controlled real-world testing.

### Added

- Docker Compose deployment for the official Ubuntu/Linux runtime target.
- Telegram administrator access and persistent runtime allowlist management.
- Expanded health endpoint and safe administrator runtime status command.
- Administrator cleanup command for expired generated files.
- Playwright screenshot, PDF, and rendered HTML exports.
- Encrypted per-user, per-domain cookie sessions for browser exports.

### Known Limitations

- Windows local browser automation is best-effort. Ubuntu 24.04 or Docker Compose is the supported deployment environment.
