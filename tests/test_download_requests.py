from app.core.download_requests import DownloadRequestStore
from app.fetchers.file_detector import FileDetection


def test_download_confirmation_is_owner_bound_and_one_time() -> None:
    store = DownloadRequestStore()
    request = store.create(123, "https://example.com/export", FileDetection(
        "uncertain", "unknown_response"
    ))

    assert store.get(request.request_id, 456) is None
    assert store.get(request.request_id, 123) == request
    assert store.pop(request.request_id, 123) == request
    assert store.get(request.request_id, 123) is None
