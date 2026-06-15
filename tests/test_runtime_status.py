import asyncio
from pathlib import Path

from app.api import routes
from app.config import Settings
from app.core.access_store import add_allowed_user
from app.core.jobs import JobStore
from app.core.runtime_status import build_admin_status


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
    assert response["version"] == "1.7.2-alpha.1"
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

    assert status.version == "1.7.2-alpha.1"
    assert status.active_jobs == 1
    assert status.known_jobs == 2
    assert status.runtime_allowed_users == 1
    assert status.storage_free_bytes > 0
    assert status.cookie_import_enabled is False
    assert status.generated_directories["html"] is True
    assert status.generated_directories["pdf"] is False
