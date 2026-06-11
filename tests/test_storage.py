from collections import namedtuple

from app.core import storage


DiskUsage = namedtuple("DiskUsage", "total used free")


def test_disk_space_check_passes_with_enough_space(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        storage.shutil,
        "disk_usage",
        lambda _: DiskUsage(2_000, 1_000, 600 * 1024 * 1024),
    )

    assert storage.has_minimum_free_space(tmp_path / "downloads", 512)


def test_disk_space_check_fails_when_space_is_low(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        storage.shutil,
        "disk_usage",
        lambda _: DiskUsage(2_000, 1_000, 100 * 1024 * 1024),
    )

    assert not storage.has_minimum_free_space(tmp_path / "downloads", 512)
