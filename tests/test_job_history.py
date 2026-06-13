from app.bot.handlers import get_job_status_record
from app.core.job_history import (
    find_job_history,
    load_job_history,
    purge_job_history,
)
from app.core.jobs import JobStore


def test_completed_job_history_is_saved_with_domain_only(tmp_path) -> None:
    path = tmp_path / "jobs" / "job_history.json"
    store = JobStore(path, history_max_stored=10)
    job = store.create_job(123, "pdf", "https://example.com/private?token=secret")

    store.update_job(job.id, status="running")
    store.update_job(job.id, status="success", progress=100)

    loaded = find_job_history(path, job.id)
    assert loaded is not None
    assert loaded.url_domain == "example.com"
    assert "private" not in path.read_text(encoding="utf-8")
    assert "secret" not in path.read_text(encoding="utf-8")


def test_corrupted_job_history_falls_back_to_empty(tmp_path) -> None:
    path = tmp_path / "job_history.json"
    path.write_text("{broken", encoding="utf-8")

    assert load_job_history(path) == []


def test_status_helper_falls_back_to_persisted_history(tmp_path) -> None:
    path = tmp_path / "job_history.json"
    writer = JobStore(path)
    job = writer.create_job(123, "screenshot", "https://example.com/page")
    writer.update_job(job.id, status="success", progress=100)

    record = get_job_status_record(job.id, 123, False, JobStore(), path)

    assert record is not None
    assert getattr(record, "job_id") == job.id
    assert get_job_status_record(job.id, 456, False, JobStore(), path) is None


def test_purge_history_clears_completed_jobs_only(tmp_path) -> None:
    path = tmp_path / "job_history.json"
    store = JobStore(path)
    job = store.create_job(123, "html", "https://example.com")
    store.update_job(job.id, status="success", progress=100)

    assert purge_job_history(path) == 1
    assert load_job_history(path) == []
    assert store.get_job(job.id) is not None
