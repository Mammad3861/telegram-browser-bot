from datetime import UTC, datetime, timedelta

from app.core.rate_limit import RateLimiter, effective_rate_limit


def test_rate_limit_per_user() -> None:
    limiter = RateLimiter()
    now = datetime(2026, 6, 16, tzinfo=UTC)

    assert limiter.check(1, "actions", 2, 60, now).allowed
    assert limiter.check(1, "actions", 2, 60, now + timedelta(seconds=1)).allowed
    blocked = limiter.check(1, "actions", 2, 60, now + timedelta(seconds=2))

    assert blocked.allowed is False
    assert blocked.retry_after_seconds > 0
    assert limiter.check(2, "actions", 2, 60, now + timedelta(seconds=2)).allowed


def test_admin_rate_limit_multiplier() -> None:
    assert effective_rate_limit(20, False, 5) == 20
    assert effective_rate_limit(20, True, 5) == 100
