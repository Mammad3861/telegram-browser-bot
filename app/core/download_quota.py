from collections import defaultdict
from datetime import UTC, date, datetime


class DownloadQuota:
    def __init__(self) -> None:
        self._counts: dict[tuple[int, date], int] = defaultdict(int)

    def remaining(self, user_id: int, limit: int, now: datetime | None = None) -> int:
        today = (now or datetime.now(UTC)).date()
        return max(0, limit - self._counts[(user_id, today)])

    def consume(self, user_id: int, limit: int, now: datetime | None = None) -> bool:
        today = (now or datetime.now(UTC)).date()
        key = (user_id, today)
        if self._counts[key] >= limit:
            return False
        self._counts[key] += 1
        return True


download_quota = DownloadQuota()
