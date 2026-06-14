from datetime import UTC, datetime

from app.bot.handlers import format_job
from app.bot.i18n import text
from app.core.jobs import Job


def test_job_status_format_uses_persian_labels() -> None:
    job = Job(
        id="abc12345",
        user_id=1,
        command="pdf",
        url="https://example.com",
        status="running",
        progress=25,
        result_message=None,
        error_message=None,
        created_at=datetime.now(UTC),
    )

    output = format_job(job, "fa")

    assert text("job_id_label", "fa") in output
    assert text("status_label", "fa") in output
    assert text("job_status_running", "fa") in output
