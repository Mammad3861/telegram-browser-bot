UNITS_EN = ("B", "KB", "MB", "GB", "TB")
UNITS_FA = ("بایت", "کیلوبایت", "مگابایت", "گیگابایت", "ترابایت")


def _trim_decimal(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def format_bytes(size_bytes: int, lang: str = "en") -> str:
    size = max(0, int(size_bytes))
    units = UNITS_FA if lang == "fa" else UNITS_EN
    if size < 1024:
        return f"{size} {units[0]}"

    value = float(size)
    unit_index = 0
    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1
    return f"{_trim_decimal(value)} {units[unit_index]}"


def format_bytes_compact(size_bytes: int, lang: str = "en") -> str:
    return format_bytes(size_bytes, lang)
