import asyncio
from pathlib import Path

from app.api import routes
from app.config import Settings
from app.core.access_store import add_allowed_user
from app.core.jobs import JobStore
from app.core.runtime_status import build_admin_status, build_setup_check, readiness_payload


def make_settings(tmp_path, **overrides) -> Settings:
    values = {
        "telegram_bot_token": "",
        "cookie_encryption_key": "",
        "downloads_dir": str(tmp_path / "downloads"),
        "access_storage_path": str(tmp_path / "downloads/access/allowed_users.json"),
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_health_response_shape(tmp_path, monkeypatch) -> None:
    settings = make_settings(tmp_path)
    monkeypatch.setattr(routes, "get_settings", lambda: settings)

    response = asyncio.run(routes.health())

    assert set(response) == {
        "status",
        "version",
        "bot_configured",
        "cookie_import_enabled",
        "runtime_target",
        "storage_path_exists",
        "browser_features_configured",
    }
    assert response["status"] == "ok"
    assert response["version"] == "1.10.0-alpha.1"
    assert response["bot_configured"] is False
    assert response["cookie_import_enabled"] is False


def test_admin_status_helper(tmp_path) -> None:
    settings = make_settings(tmp_path)
    downloads_dir = Path(settings.downloads_dir)
    (downloads_dir / "html").mkdir(parents=True)
    add_allowed_user(
        Path(settings.access_storage_path), 123, added_by=999, note="tester"
    )

    store = JobStore()
    active = store.create_job(1, "html", "https://example.com")
    store.update_job(active.id, status="running")
    finished = store.create_job(2, "pdf", "https://example.org")
    store.update_job(finished.id, status="success", progress=100)

    status = build_admin_status(settings, store)

    assert status.version == "1.10.0-alpha.1"
    assert status.active_jobs == 1
    assert status.known_jobs == 2
    assert status.recent_completed_jobs >= 0
    assert status.runtime_allowed_users == 1
    assert status.storage_free_bytes > 0
    assert status.cookie_import_enabled is False
    assert status.downloads_dir == str(downloads_dir)
    assert status.search_provider == "duckduckgo_html"
    assert status.download_mode == "safe"
    assert status.generated_directories["html"] is True
    assert status.generated_directories["pdf"] is False


def test_health_live_response_shape() -> None:
    response = asyncio.run(routes.health_live())

    assert response == {"status": "ok", "version": "1.10.0-alpha.1"}


def test_health_ready_success(tmp_path) -> None:
    settings = make_settings(tmp_path, min_free_disk_mb=0)

    response = readiness_payload(settings)

    assert response["status"] in {"ok", "degraded"}
    checks = response["checks"]
    assert checks["downloads_writable"] is True
    assert checks["persistent_store_dirs_writable"] is True
    assert checks["search_provider_valid"] is True
    assert checks["disk_free_above_minimum"] is True
    assert isinstance(response["free_bytes"], int)
    assert isinstance(response["free_human"], str)


def test_health_ready_failure_for_invalid_search_provider(tmp_path) -> None:
    settings = make_settings(tmp_path, search_provider="bad_provider")

    response = readiness_payload(settings)

    assert response["status"] == "degraded"
    assert response["checks"]["search_provider_valid"] is False


def test_setup_check_helper_has_safe_summary(tmp_path) -> None:
    settings = make_settings(
        tmp_path,
        telegram_bot_token="secret-token",
        admin_telegram_ids="123",
        min_free_disk_mb=0,
    )

    check = build_setup_check(settings)

    assert check.bot_token_configured is True
    assert check.admin_ids_configured is True
    assert check.downloads_writable is True
    assert check.persistent_store_dirs_writable is True
    assert check.free_disk_ok is True
    assert check.search_provider_status == "duckduckgo_html"
