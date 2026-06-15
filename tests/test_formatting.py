from app.core.formatting import format_bytes


def test_format_bytes_persian_units() -> None:
    assert format_bytes(0, "fa") == "0 بایت"
    assert format_bytes(512, "fa") == "512 بایت"
    assert format_bytes(1024, "fa") == "1 کیلوبایت"
    assert format_bytes(1536, "fa") == "1.5 کیلوبایت"
    assert format_bytes(1048576, "fa") == "1 مگابایت"
    assert format_bytes(1073741824, "fa") == "1 گیگابایت"
    assert "گیگابایت" in format_bytes(9289396224, "fa")


def test_format_bytes_english_units() -> None:
    assert format_bytes(0) == "0 B"
    assert format_bytes(512) == "512 B"
    assert format_bytes(1024) == "1 KB"
    assert format_bytes(1536) == "1.5 KB"
    assert format_bytes(1048576) == "1 MB"
    assert format_bytes(1073741824) == "1 GB"
    assert format_bytes(9289396224) == "8.65 GB"
