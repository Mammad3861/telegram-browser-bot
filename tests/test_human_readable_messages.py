from pathlib import Path

from app.bot.handlers import format_admin_status, format_setup_check, format_storage_summary
from app.core.runtime_status import AdminStatus, SetupCheck
from app.core.storage_diagnostics import StorageSummary


def test_storage_output_uses_human_readable_persian_sizes() -> None:
    summary = StorageSummary(
        downloads_dir=Path("downloads"),
        free_bytes=9289396224,
        cleanup_max_age_hours=24,
        categories={
            "files": 0,
            "screenshots": 512,
            "pdf": 1024,
            "html": 1536,
            "html_rendered": 1048576,
            "sessions": 0,
            "policies": 488,
            "jobs": 3707,
            "ui_sessions": 28730,
        },
    )

    output = format_storage_summary(summary, "fa")

    assert "گیگابایت" in output
    assert "28.06 کیلوبایت" in output
    assert "28730 بایت" not in output
    assert "9289396224" not in output
    assert "ui_sessions" not in output
    assert "نشست‌های رابط کاربری" in output
    assert "تصویرهای صفحه" in output


def test_storage_output_uses_readable_english_labels() -> None:
    summary = StorageSummary(
        downloads_dir=Path("downloads"),
        free_bytes=1024,
        cleanup_max_age_hours=24,
        categories={"files": 0, "screenshots": 0, "html_rendered": 0, "ui_sessions": 0},
    )

    output = format_storage_summary(summary, "en")

    assert "Files: 0 B" in output
    assert "Screenshots: 0 B" in output
    assert "Rendered HTML: 0 B" in output
    assert "UI sessions: 0 B" in output


def test_admin_status_uses_human_readable_free_disk() -> None:
    status = AdminStatus(
        version="1.10.0-alpha.1",
        runtime_target="Linux/Ubuntu 24.04 or Docker",
        uptime_seconds=5,
        downloads_dir="downloads",
        active_jobs=0,
        known_jobs=0,
        recent_completed_jobs=0,
        runtime_allowed_users=0,
        storage_free_bytes=9289396224,
        cookie_import_enabled=False,
        generated_directories={"html": True},
        url_sessions=0,
        search_sessions=0,
        browser_tab_sessions=0,
        content_policy_enabled=True,
        search_provider="duckduckgo_html",
        command_menu_mode="auto",
        download_mode="safe",
        cleanup_max_age_hours=24,
        cleanup_after_send_enabled=True,
        browser_features_configured=False,
    )

    output = format_admin_status(status, "fa")

    assert "گیگابایت" in output
    assert "9289396224" not in output


def test_setup_check_output_redacts_secrets() -> None:
    check = SetupCheck(
        bot_token_configured=True,
        admin_ids_configured=True,
        downloads_writable=True,
        persistent_store_dirs_writable=True,
        free_disk_ok=True,
        browser_ready=False,
        search_provider_status="duckduckgo_html",
        command_menu_mode="auto",
        content_policy_enabled=True,
        cookie_import_enabled=False,
        health_ready=False,
    )

    output = format_setup_check(check, "en")

    assert "Setup check" in output
    assert "secret" not in output.lower()
    assert "token" in output.lower()
    assert "duckduckgo_html" in output


def test_setup_check_persian_output() -> None:
    check = SetupCheck(
        bot_token_configured=False,
        admin_ids_configured=True,
        downloads_writable=True,
        persistent_store_dirs_writable=True,
        free_disk_ok=True,
        browser_ready=True,
        search_provider_status="disabled",
        command_menu_mode="auto",
        content_policy_enabled=False,
        cookie_import_enabled=False,
        health_ready=True,
    )

    output = format_setup_check(check, "fa")

    assert "بررسی راه‌اندازی" in output
    assert "نیازمند بررسی" in output
    assert "disabled" in output
