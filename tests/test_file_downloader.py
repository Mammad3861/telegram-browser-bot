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


def run_download(
    handler, tmp_path, max_size_mb=1, url="https://example.com/file.pdf", allow_uncertain=False
):
    async def execute():
        async with FileDownloader(transport=httpx.MockTransport(handler)) as downloader:
            downloader._validate_destination = allow_test_destination  # type: ignore[method-assign]
            return await downloader.download(
                url,
                tmp_path,
                max_size_mb=max_size_mb,
                minimum_free_mb=0,
                allow_uncertain=allow_uncertain,
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


def test_downloads_github_codeload_zip(tmp_path) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/zip"},
            stream=ChunkStream([b"zip"]),
        )

    result = run_download(
        handler,
        tmp_path,
        url="https://codeload.github.com/example/project/zip/refs/heads/main",
    )

    assert result.size == 3


def test_follows_redirect_to_direct_file(tmp_path) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/start":
            return httpx.Response(302, headers={"location": "/file.msi"})
        return httpx.Response(
            200,
            headers={"content-type": "application/octet-stream"},
            stream=ChunkStream([b"installer"]),
        )

    result = run_download(handler, tmp_path, url="https://example.com/start")

    assert result.filename == "file.msi"


def test_unknown_response_requires_explicit_uncertain_mode(tmp_path) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/x-custom"},
            stream=ChunkStream([b"binary data"]),
        )

    with pytest.raises(DownloadError, match="direct file links"):
        run_download(handler, tmp_path, url="https://example.com/export")

    result = run_download(
        handler, tmp_path, url="https://example.com/export", allow_uncertain=True
    )
    assert result.size == len(b"binary data")


def test_confirmed_unknown_html_is_still_rejected(tmp_path) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "application/x-custom"},
            stream=ChunkStream([b"<!doctype html><html></html>"]),
        )

    with pytest.raises(DownloadError, match="HTML page"):
        run_download(
            handler, tmp_path, url="https://example.com/export", allow_uncertain=True
        )


def test_misleading_html_header_with_file_extension_uses_body_sniff(tmp_path) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/html"},
            stream=ChunkStream([b"MZ binary installer"]),
        )

    result = run_download(
        handler,
        tmp_path,
        url="https://example.com/installer.msi",
        allow_uncertain=True,
    )
    assert result.filename == "installer.msi"


def test_explicit_html_attachment_is_allowed(tmp_path) -> None:
    async def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={
                "content-type": "text/html",
                "content-disposition": 'attachment; filename="page.html"',
            },
            stream=ChunkStream([b"<!doctype html><html></html>"]),
        )

    result = run_download(handler, tmp_path, url="https://example.com/export")
    assert result.filename == "page.html"
