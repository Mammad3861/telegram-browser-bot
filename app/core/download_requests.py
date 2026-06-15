import secrets
from dataclasses import dataclass

from app.fetchers.file_detector import FileDetection


@dataclass(frozen=True)
class PendingDownload:
    request_id: str
    user_id: int
    url: str
    detection: FileDetection
    admin_force_allowed: bool = False


class DownloadRequestStore:
    def __init__(self) -> None:
        self._requests: dict[str, PendingDownload] = {}

    def create(
        self,
        user_id: int,
        url: str,
        detection: FileDetection,
        admin_force_allowed: bool = False,
    ) -> PendingDownload:
        request = PendingDownload(
            secrets.token_hex(4), user_id, url, detection, admin_force_allowed
        )
        self._requests[request.request_id] = request
        return request

    def get(self, request_id: str, user_id: int) -> PendingDownload | None:
        request = self._requests.get(request_id)
        return request if request and request.user_id == user_id else None

    def pop(self, request_id: str, user_id: int) -> PendingDownload | None:
        request = self.get(request_id, user_id)
        if request:
            self._requests.pop(request_id, None)
        return request


download_request_store = DownloadRequestStore()
