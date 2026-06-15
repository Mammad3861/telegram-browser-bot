# Command Reference

Telegram's native Menu button contains only common commands. `/start` and `/menu` open a button-first browser home with Search, New URL, Sessions, Recent jobs, Language, and Help. Advanced commands remain available by typing them directly.

English and Persian preferences cover menus, URL/search cards, buttons, jobs, admin text tools, and common bot messages. Telegram clients may cache native command descriptions briefly after the bot registers updated `language_code="fa"` commands; reopening the chat or restarting the client usually refreshes them.

## Public Commands

| Command | Description |
| --- | --- |
| `/start` | Start the bot and show the welcome text. |
| `/menu` | Open the interactive menu. |
| `/help` | Show concise help. |
| `/language [en\|fa]` | Show or change the interface language. |
| `/about` | Show version and runtime information. |
| `/whoami` | Show your Telegram ID. |

Examples:

```text
/language en
/language fa
/menu
```

Persian: برای تغییر زبان از `/language fa` و برای باز کردن منو از `/menu` استفاده کنید.

## Protected Commands

These require an administrator or allowed user.

| Command | Description |
| --- | --- |
| `/search <query>` | Search using the configured provider. |
| `/fetch <url>` | Fetch and display page text. |
| `/links <url>` | Extract links from a page. |
| `/html <url>` | Export server-provided HTTP HTML. |
| `/html_rendered <url>` | Export Playwright-rendered HTML. |
| `/rendered_html <url>` | Alias for `/html_rendered`. |
| `/download <url>` | Download a direct file or confirm an uncertain candidate when configured. |
| `/screenshot <url>` | Capture a full-page PNG. |
| `/pdf <url>` | Export a page as PDF. |
| `/status <job_id>` | Show an active or historical job. |
| `/jobs` | List recent active and completed jobs. |
| `/cancel <job_id>` | Cancel an owned active job. |
| `/cookies_help` | Show cookie import guidance. |
| `/cookies_import <domain>` | Begin encrypted cookie import. |
| `/sessions` | List saved cookie-session domains. |
| `/delete_session <domain>` | Delete one saved cookie session. |

You can also send a single public URL without a command to create a persistent browser tab card. Its buttons provide Back, Refresh, Links, Screenshot, PDF, HTML, Rendered HTML, direct Download, Page options, and Close actions.

Find downloads scans visible page links for normal file candidates and lets the user choose one. It does not auto-download files, inspect streaming manifests, or extract protected streams. Uncertain attempts show metadata and a risk-acceptance confirmation. Users must download only files they are authorized to receive.

Page options lists up to the configured number of visible links and simple buttons. A selected option updates the tab URL/title and, when encryption is configured, saves browser storage for later tab actions. It may help with cookie consent and simple age-confirmation screens. It never fills forms, submits passwords, or automatically passes age/consent gates; the user must choose an option explicitly.

Examples:

```text
/search Python 3.12 documentation
/screenshot https://example.com
/pdf https://example.com
```

فارسی: یک نشانی عمومی مانند `https://example.com` بفرستید تا تب مرورگر باز شود.

## Admin Commands

| Command | Description |
| --- | --- |
| `/access` | Show current access configuration counts. |
| `/allow <telegram_id> [note]` | Add a runtime allowed user. |
| `/deny <telegram_id>` | Remove a runtime allowed user. |
| `/allowed_users` | List static and runtime allowed users. |
| `/admin_status` | Show safe runtime and storage diagnostics. |
| `/cleanup` | Delete old generated files. |
| `/cleanup dry_run` | Show what cleanup would delete without deleting files. |
| `/storage` | Show downloads directory usage by category. |
| `/purge_history` | Clear completed-job history without touching active jobs. |
| `/texts` | List editable bot text keys and languages. |
| `/set_text <key> <lang> <text>` | Set `welcome`, `help`, or `about`. |
| `/reset_text <key> [lang]` | Reset an editable text override. |
| `/preview_text <key> [lang]` | Preview the effective text. |
| `/policy` | Show content policy state and rule counts. |
| `/categories` | Show every category as blocked, allowed, or neutral. |
| `/block_category <category>` | Block a category. |
| `/allow_category <category>` | Explicitly allow a category. |
| `/unblock_category <category>` | Remove a category block. |
| `/unallow_category <category>` | Remove an explicit category allow. |
| `/category_domains <category>` | List domains classified in a category. |
| `/add_category_domain <category> <domain>` | Classify a domain under a category. |
| `/remove_category_domain <category> <domain>` | Remove a domain from a category. |
| `/block_domain <domain> [category]` | Block a domain, optionally adding it to a category list. |
| `/allow_domain <domain>` | Explicitly allow a domain. |
| `/unblock_domain <domain>` | Remove blocked/category rules for a domain. |
| `/unallow_domain <domain>` | Remove an explicit allow rule. |
| `/policy_test <url>` | Show the current decision for a URL. |
| `/policy_reload` | Reload and summarize the policy file. |
| `/routes` | List configured domain route rules. |
| `/route_domain <domain> <default\|proxy>` | Set a domain route. |
| `/unroute_domain <domain>` | Remove a domain route rule. |
| `/route_test <url>` | Show the selected route or missing configuration. |
| `/refresh_commands` | Re-register Telegram native command menus. |

Valid policy categories are `adult`, `gambling`, `crypto`, `malware`, `phishing`, `dangerous`, `media`, and `custom`. Built-in lists classify domains only; administrators choose which categories are blocked. Allowing `media` does not enable protected-streaming downloads.

Examples:

```text
/allow 123456789 teammate
/set_text welcome fa خوش آمدید
/cleanup
/cleanup dry_run
/storage
```
