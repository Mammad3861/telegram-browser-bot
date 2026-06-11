from datetime import UTC, datetime

from app.core.download_quota import DownloadQuota


def test_per_user_daily_download_quota() -> None:
    quota = DownloadQuota()
    now = datetime(2026, 6, 11, tzinfo=UTC)

    assert quota.consume(10, 2, now)
    assert quota.consume(10, 2, now)
    assert not quota.consume(10, 2, now)
    assert quota.consume(20, 2, now)
