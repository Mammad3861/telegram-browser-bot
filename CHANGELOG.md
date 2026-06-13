# Changelog

All notable changes to this project are documented in this file.

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
