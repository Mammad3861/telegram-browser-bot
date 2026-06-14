# Cookie Sessions

Cookie import supports existing browser sessions for Playwright-rendered HTML, screenshots, and PDFs. The bot does not implement username/password login.

## Setup

Generate a Fernet encryption key:

```bash
python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Set it in `.env`:

```env
COOKIE_ENCRYPTION_KEY=generated_key
ENABLE_COOKIE_IMPORT=true
SESSION_STORAGE_DIR=downloads/sessions
```

Without a key, cookie import is disabled while the rest of the bot continues working.

## Import Format

Run:

```text
/cookies_import example.com
```

Then send a Playwright-compatible JSON list:

```json
[
  {
    "name": "session",
    "value": "cookie-value",
    "domain": ".example.com",
    "path": "/",
    "secure": true,
    "httpOnly": true
  }
]
```

## Security

- Sessions are isolated per Telegram user and normalized domain.
- Cookie files are encrypted locally under `downloads/sessions`.
- Cookie values are not echoed in bot responses or logs.
- Do not import cookies from untrusted sources.
- Treat the encryption key and `downloads/sessions` as sensitive data.
- Keep the same encryption key across deployments or existing sessions cannot be decrypted.
- HTTPX commands such as `/fetch` and `/html` do not use saved browser cookies.
- No username/password credentials are requested or stored.
