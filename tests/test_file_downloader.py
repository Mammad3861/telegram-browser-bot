import asyncio
import hashlib

import httpx
import pytest

from app.fetchers.file_downloader import DownloadError, FileDownloader


class ChunkStream(httpx.AsyncByteStream):
    def __init__(self, chunks: list[bytes]) -> None:
        self.chunks = chunks

    async def __aiter__(self):
        for chunk in self.chunks:
            yield chunk


async def allow_test_destination(_: str) -> None:
    return None


def run_download(handler, tmp_path, max_size_mb=1, url="https://example.com/file.pdf"):
    async def execute():
        async with FileDownloader(transport=httpx.MockTransport(handler)) as downloader:
            downloader._validate_destination = allow_test_destination  # type: ignore[method-assign]
            return await downloader.download(
                url,
                tmp_path,
                max_size_mb=max_size_mb,
                minimum_free_mb=0,
            )

    return asyncio.run(execute())


def test_rejects_oversized_content_length(tmp_path) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "content-type": "application/pdf",
                "content-length": str(2 * 1024 * 1024),
            },
            stream=ChunkStream([]),
        )

    with pytest.raises(DownloadError, match="exceeds the 1 MB"):
        run_download(handler, tmp_path)

    assert list((tmp_path / "files").iterdir()) == []


def test_stops_stream_when_download_exceeds_limit(tmp_path) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/pdf"},
            stream=ChunkStream([b"a" * 700_000, b"b" * 700_000]),
        )

    with pytest.raises(DownloadError, match="exceeds the 1 MB"):
        run_download(handler, tmp_path)

    assert list((tmp_path / "files").iterdir()) == []


def test_streams_file_and_calculates_sha256(tmp_path) -> None:
    content = b"first chunk" + b"second chunk"

    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "content-type": "application/pdf",
                "content-disposition": 'attachment; filename="report.pdf"',
            },
            stream=ChunkStream([b"first chunk", b"second chunk"]),
        )

    result = run_download(handler, tmp_path)

    assert result.filename == "report.pdf"
    assert result.size == len(content)
    assert result.sha256 == hashlib.sha256(content).hexdigest()
    assert result.path.read_bytes() == content


def test_rejects_normal_html_page(tmp_path) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            stream=ChunkStream([b"<html></html>"]),
        )

    with pytest.raises(
        DownloadError, match="This version only supports direct file links"
    ):
        run_download(handler, tmp_path, url="https://example.com/page")
