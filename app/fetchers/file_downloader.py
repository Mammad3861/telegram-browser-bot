import hashlib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import httpx

from app.core.storage import ensure_free_space
from app.core.url_validation import validate_url
from app.fetchers.file_detector import (
    FileDetection,
    choose_filename,
    detect_file,
    looks_like_html,
)
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
        proxy_url: str | None = None,
    ) -> None:
        super().__init__(transport=transport, max_response_bytes=0, proxy_url=proxy_url)

    async def inspect(self, url: str, max_size_mb: int) -> FileDetection:
        current_url = validate_url(url)
        max_bytes = max_size_mb * 1024 * 1024
        for _ in range(6):
            await self._validate_destination(current_url)
            try:
                response = await self.client.head(current_url)
            except httpx.HTTPError:
                fallback = detect_file(current_url)
                return fallback if fallback.confident else FileDetection(
                    "uncertain", "head_unavailable", final_url=current_url
                )
            if response.status_code >= 400:
                fallback = detect_file(str(response.url))
                return fallback if fallback.confident else FileDetection(
                    "uncertain", "head_unavailable", final_url=str(response.url)
                )
            if response.is_redirect:
                location = response.headers.get("location")
                if not location:
                    return FileDetection("uncertain", "redirect_without_location", final_url=current_url)
                current_url = urljoin(str(response.url), location)
                continue
            length = response.headers.get("content-length")
            try:
                content_length = int(length) if length else None
            except ValueError:
                content_length = None
            if content_length is not None and content_length > max_bytes:
                raise DownloadError(f"File exceeds the {max_size_mb} MB download limit")
            return detect_file(
                str(response.url),
                response.headers.get("content-type"),
                response.headers.get("content-disposition"),
                content_length,
            )
        raise DownloadError("Too many redirects")

    async def download(
        self,
        url: str,
        downloads_dir: Path,
        max_size_mb: int,
        minimum_free_mb: int,
        allow_uncertain: bool = False,
    ) -> DownloadResult:
        current_url = validate_url(url)
        max_bytes = max_size_mb * 1024 * 1024
        files_dir = downloads_dir / "files"
        ensure_free_space(files_dir, minimum_free_mb)

        try:
            for _ in range(6):
                await self._validate_destination(current_url)
                try:
                    head = await self.client.head(current_url)
                    if head.is_redirect:
                        location = head.headers.get("location")
                        if location:
                            current_url = urljoin(str(head.url), location)
                            continue
                    if head.status_code < 400:
                        length = head.headers.get("content-length")
                        if length and int(length) > max_bytes:
                            raise DownloadError(
                                f"File exceeds the {max_size_mb} MB download limit"
                            )
                except (httpx.HTTPError, ValueError):
                    pass
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
                    detection = detect_file(
                        str(response.url), content_type, disposition
                    )
                    if detection.confidence == "rejected" or (
                        not detection.confident and not allow_uncertain
                    ):
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
                            first_chunk = True
                            async for chunk in response.aiter_bytes():
                                if first_chunk:
                                    first_chunk = False
                                    if looks_like_html(chunk) and not (
                                        disposition
                                        and "attachment" in disposition.lower()
                                    ):
                                        raise DownloadError(
                                            "The response is an HTML page, not a downloadable file."
                                        )
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
