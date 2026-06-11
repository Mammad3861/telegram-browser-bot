import hashlib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import httpx

from app.core.storage import ensure_free_space
from app.core.url_validation import validate_url
from app.fetchers.file_detector import choose_filename, is_direct_file
from app.fetchers.http_fetcher import FetchError, HttpFetcher


class DownloadError(FetchError):
    pass


@dataclass(frozen=True)
class DownloadResult:
    path: Path
    filename: str
    content_type: str
    size: int
    sha256: str


def _unique_path(directory: Path, filename: str) -> Path:
    path = directory / filename
    counter = 1
    while path.exists():
        path = directory / f"{Path(filename).stem}_{counter}{Path(filename).suffix}"
        counter += 1
    return path


class FileDownloader(HttpFetcher):
    def __init__(
        self,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(transport=transport, max_response_bytes=0)

    async def download(
        self,
        url: str,
        downloads_dir: Path,
        max_size_mb: int,
        minimum_free_mb: int,
    ) -> DownloadResult:
        current_url = validate_url(url)
        max_bytes = max_size_mb * 1024 * 1024
        files_dir = downloads_dir / "files"
        ensure_free_space(files_dir, minimum_free_mb)

        try:
            for _ in range(6):
                await self._validate_destination(current_url)
                async with self.client.stream("GET", current_url) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise DownloadError("Redirect response has no location")
                        current_url = urljoin(str(response.url), location)
                        continue

                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "application/octet-stream")
                    disposition = response.headers.get("content-disposition")
                    if not is_direct_file(str(response.url), content_type, disposition):
                        raise DownloadError("This version only supports direct file links.")

                    content_length = response.headers.get("content-length")
                    if content_length:
                        try:
                            declared_size = int(content_length)
                        except ValueError:
                            declared_size = 0
                        if declared_size > max_bytes:
                            raise DownloadError(
                                f"File exceeds the {max_size_mb} MB download limit"
                            )

                    filename = choose_filename(str(response.url), disposition)
                    output_path = _unique_path(files_dir, filename)
                    digest = hashlib.sha256()
                    downloaded = 0

                    try:
                        with output_path.open("xb") as output:
                            async for chunk in response.aiter_bytes():
                                downloaded += len(chunk)
                                if downloaded > max_bytes:
                                    raise DownloadError(
                                        f"File exceeds the {max_size_mb} MB download limit"
                                    )
                                output.write(chunk)
                                digest.update(chunk)
                    except BaseException:
                        output_path.unlink(missing_ok=True)
                        raise

                    return DownloadResult(
                        path=output_path,
                        filename=output_path.name,
                        content_type=content_type.split(";", 1)[0].strip(),
                        size=downloaded,
                        sha256=digest.hexdigest(),
                    )
        except httpx.TimeoutException as exc:
            raise DownloadError("The download timed out") from exc
        except httpx.ConnectError as exc:
            raise DownloadError("Could not connect to the remote site") from exc
        except httpx.HTTPStatusError as exc:
            raise DownloadError(
                f"The remote site returned HTTP {exc.response.status_code}"
            ) from exc
        except httpx.HTTPError as exc:
            raise DownloadError(f"Download failed ({type(exc).__name__})") from exc

        raise DownloadError("Too many redirects")
