# Release Notes Template

## Highlights

- 

## Upgrade Notes

- 

## Docker Deployment

```bash
docker compose up -d --build
docker compose logs -f
curl http://127.0.0.1:18080/health/ready
```

## New Settings

- None.

## Breaking Changes

- None known.

## Security Notes

- No secrets are included in release artifacts.
- Do not commit `.env` or `downloads/`.
- The bot does not bypass CAPTCHA, DRM, paywalls, or login restrictions.

## Known Limitations

- Some websites may not work fully in a headless browser.
- Protected streaming downloads are not supported.
- Username/password storage is not supported.
- Windows local development is best-effort only.

## Test Summary

```text
python -m pytest -q -p no:cacheprovider
```
