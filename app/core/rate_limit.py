from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    limit: int
    retry_after_seconds: int


class RateLimiter:
    def __init__(self) -> None:
        self._events: dict[tuple[int, str], deque[datetime]] = defaultdict(deque)

    def check(
        self,
        user_id: int,
        bucket: str,
        limit: int,
        window_seconds: int,
        now: datetime | None = None,
    ) -> RateLimitResult:
        current = now or datetime.now(UTC)
        events = self._events[(user_id, bucket)]
        cutoff = current - timedelta(seconds=window_seconds)
        while events and events[0] <= cutoff:
            events.popleft()
        if len(events) >= limit:
            retry_after = int((events[0] + timedelta(seconds=window_seconds) - current).total_seconds())
            return RateLimitResult(False, limit, max(1, retry_after))
        events.append(current)
        return RateLimitResult(True, limit, 0)


def effective_rate_limit(limit: int, is_admin: bool, multiplier: int) -> int:
    if is_admin:
        return max(limit, limit * max(1, multiplier))
    return limit


rate_limiter = RateLimiter()
