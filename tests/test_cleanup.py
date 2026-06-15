import os
from datetime import UTC, datetime, timedelta

from app.core.cleanup import cleanup_generated_files


NOW = datetime(2026, 6, 12, 12, 0, tzinfo=UTC)


def set_file_age(path, age_hours: int) -> None:
    timestamp = (NOW - timedelta(hours=age_hours)).timestamp()
    os.utime(path, (timestamp, timestamp))


def test_cleanup_deletes_old_generated_files(tmp_path) -> None:
    old_file = tmp_path / "html" / "old.html"
    old_file.parent.mkdir(parents=True)
    old_file.write_bytes(b"old output")
    set_file_age(old_file, 25)

    result = cleanup_generated_files(tmp_path, max_age_hours=24, now=NOW)

    assert not old_file.exists()
    assert result.deleted_files == 1
    assert result.freed_bytes == len(b"old output")
    assert result.dry_run is False


def test_cleanup_dry_run_keeps_old_generated_files(tmp_path) -> None:
    old_file = tmp_path / "pdf" / "old.pdf"
    old_file.parent.mkdir(parents=True)
    old_file.write_bytes(b"old output")
    set_file_age(old_file, 25)

    result = cleanup_generated_files(tmp_path, max_age_hours=24, now=NOW, dry_run=True)

    assert old_file.exists()
    assert result.deleted_files == 1
    assert result.freed_bytes == len(b"old output")
    assert result.dry_run is True


def test_cleanup_keeps_recent_generated_files(tmp_path) -> None:
    recent_file = tmp_path / "screenshots" / "recent.png"
    recent_file.parent.mkdir(parents=True)
    recent_file.write_bytes(b"recent output")
    set_file_age(recent_file, 1)

    result = cleanup_generated_files(tmp_path, max_age_hours=24, now=NOW)

    assert recent_file.exists()
    assert result.deleted_files == 0
    assert result.freed_bytes == 0


def test_cleanup_never_touches_sessions_or_access(tmp_path) -> None:
    protected_files = [
        tmp_path / "sessions" / "123" / "example.com.json",
        tmp_path / "access" / "allowed_users.json",
        tmp_path / "preferences" / "user_preferences.json",
        tmp_path / "texts" / "bot_texts.json",
        tmp_path / "ui_sessions" / "url_sessions.json",
        tmp_path / "ui_sessions" / "search_sessions.json",
        tmp_path / "jobs" / "job_history.json",
        tmp_path / "policies" / "content_policy.json",
        tmp_path / "policies" / "route_rules.json",
    ]
    for path in protected_files:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("protected", encoding="utf-8")
        set_file_age(path, 100)

    result = cleanup_generated_files(tmp_path, max_age_hours=24, now=NOW)

    assert all(path.exists() for path in protected_files)
    assert result.deleted_files == 0
