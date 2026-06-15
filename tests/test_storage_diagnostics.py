from app.core.storage_diagnostics import build_storage_summary


def test_storage_summary_counts_categories(tmp_path) -> None:
    output = tmp_path / "downloads" / "screenshots" / "shot.png"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"12345")

    summary = build_storage_summary(tmp_path / "downloads", cleanup_max_age_hours=24)

    assert summary.categories["screenshots"] == 5
    assert summary.categories["pdf"] == 0
    assert summary.free_bytes > 0
    assert summary.cleanup_max_age_hours == 24
