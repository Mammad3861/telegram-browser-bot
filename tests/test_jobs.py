import pytest

from app.core.jobs import JobLimitError, JobStore


def test_job_creation() -> None:
    store = JobStore()
    job = store.create_job(10, "html", "https://example.com")

    assert len(job.id) == 8
    assert job.user_id == 10
    assert job.status == "pending"
    assert job.progress == 0
    assert store.get_job(job.id) == job


def test_job_status_transitions_set_timestamps() -> None:
    store = JobStore()
    job = store.create_job(10, "download", "https://example.com/file.pdf")

    running = store.update_job(job.id, status="running", progress=25)
    assert running is not None
    assert running.status == "running"
    assert running.started_at is not None
    assert running.progress == 25

    finished = store.update_job(
        job.id, status="success", progress=100, result_message="done"
    )
    assert finished is not None
    assert finished.status == "success"
    assert finished.finished_at is not None
    assert finished.result_message == "done"


def test_per_user_concurrency_limit() -> None:
    store = JobStore()
    store.create_job(10, "html", "https://example.com", max_per_user=1)

    with pytest.raises(JobLimitError, match="maximum number of active jobs"):
        store.create_job(
            10,
            "download",
            "https://example.com/file.pdf",
            max_global=3,
            max_per_user=1,
        )


def test_global_concurrency_limit() -> None:
    store = JobStore()
    store.create_job(10, "html", "https://example.com", max_global=2)
    store.create_job(20, "html", "https://example.org", max_global=2)

    with pytest.raises(JobLimitError, match="Global job limit"):
        store.create_job(30, "html", "https://example.net", max_global=2)


def test_user_cannot_cancel_another_users_job() -> None:
    store = JobStore()
    job = store.create_job(10, "html", "https://example.com")

    assert not store.cancel_job(job.id, user_id=20)
    assert store.get_job(job.id).status == "pending"  # type: ignore[union-attr]


def test_admin_can_cancel_any_job() -> None:
    store = JobStore()
    job = store.create_job(10, "html", "https://example.com")

    assert store.cancel_job(job.id, user_id=99, is_admin=True)
    cancelled = store.get_job(job.id)
    assert cancelled is not None
    assert cancelled.status == "cancelled"
    assert cancelled.finished_at is not None
