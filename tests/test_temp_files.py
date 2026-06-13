from pathlib import Path

import pytest

from app.core.temp_files import (
    cleanup_sent_file,
    delete_generated_file,
    is_safe_generated_file,
)


@pytest.mark.parametrize(
    "category", ["screenshots", "pdf", "html", "html_rendered", "files"]
)
def test_safe_delete_accepts_generated_file_categories(tmp_path, category) -> None:
    downloads = tmp_path / "downloads"
    output = downloads / category / "output.bin"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"generated")

    assert is_safe_generated_file(output, downloads)
    assert delete_generated_file(output, downloads)
    assert not output.exists()


@pytest.mark.parametrize("category", ["sessions", "access"])
def test_safe_delete_rejects_persistent_categories(tmp_path, category) -> None:
    downloads = tmp_path / "downloads"
    protected = downloads / category / "data.json"
    protected.parent.mkdir(parents=True)
    protected.write_text("persistent", encoding="utf-8")

    assert not is_safe_generated_file(protected, downloads)
    assert not delete_generated_file(protected, downloads)
    assert protected.exists()


def test_safe_delete_rejects_file_outside_downloads(tmp_path) -> None:
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("keep", encoding="utf-8")

    assert not is_safe_generated_file(outside, downloads)
    assert not delete_generated_file(outside, downloads)
    assert outside.exists()


def test_cleanup_after_send_deletes_when_enabled(tmp_path) -> None:
    downloads = tmp_path / "downloads"
    output = downloads / "pdf" / "output.pdf"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"pdf")

    assert cleanup_sent_file(output, downloads, delete_after_send=True)
    assert not output.exists()


def test_cleanup_after_send_keeps_file_when_disabled(tmp_path) -> None:
    downloads = tmp_path / "downloads"
    output = downloads / "html" / "output.html"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"html")

    assert not cleanup_sent_file(output, downloads, delete_after_send=False)
    assert output.exists()


def test_cleanup_failure_is_non_fatal(tmp_path, monkeypatch) -> None:
    downloads = tmp_path / "downloads"
    output = downloads / "screenshots" / "output.png"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"png")

    def fail_unlink(_: Path) -> None:
        raise OSError("simulated deletion failure")

    monkeypatch.setattr(Path, "unlink", fail_unlink)

    assert not cleanup_sent_file(output, downloads, delete_after_send=True)
    assert output.exists()

