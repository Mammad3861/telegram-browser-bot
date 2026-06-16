# Migration Notes

These notes are for alpha users upgrading an existing deployment.

## Persistent Data

`downloads/` contains runtime data that should survive rebuilds and restarts.

Do not delete these folders unless you intentionally want to reset that data:

- `downloads/preferences`
- `downloads/texts`
- `downloads/access`
- `downloads/sessions`
- `downloads/policies`
- `downloads/ui_sessions`
- `downloads/jobs`

Generated output folders such as `downloads/html`, `downloads/html_rendered`, `downloads/files`, `downloads/screenshots`, and `downloads/pdf` may contain temporary leftovers. Admins can preview cleanup with `/cleanup dry_run`.

## JSON Stores

Local JSON stores are loaded defensively. Older stores may be auto-migrated by newer code, and corrupted stores should fail safely where supported instead of crashing the bot.

## Upgrade Process

```bash
docker compose down
cp -a downloads downloads.backup.$(date +%Y%m%d%H%M%S)
git pull
docker compose up -d --build
curl http://127.0.0.1:18080/health/ready
```

After startup, run `/setup_check`, `/admin_status`, and `/storage`.
