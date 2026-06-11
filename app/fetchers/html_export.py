import gzip
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

from app.core.storage import ensure_free_space


def safe_html_filename(url: str, timestamp: datetime | None = None) -> str:
    hostname = urlparse(url).hostname or "page"
    safe_domain = re.sub(r"[^a-zA-Z0-9.-]+", "_", hostname).strip("._-") or "page"
    created_at = timestamp or datetime.now(UTC)
    return f"{safe_domain}_{created_at.strftime('%Y%m%d_%H%M%S')}.html"


def save_html(
    content: bytes,
    url: str,
    downloads_dir: Path,
    compress_above_mb: int = 5,
    minimum_free_mb: int = 512,
    timestamp: datetime | None = None,
) -> Path:
    html_dir = downloads_dir / "html"
    ensure_free_space(html_dir, minimum_free_mb)
    output_path = html_dir / safe_html_filename(url, timestamp)

    if len(content) > compress_above_mb * 1024 * 1024:
        output_path = output_path.with_suffix(".html.gz")
        with gzip.open(output_path, "wb") as archive:
            archive.write(content)
    else:
        output_path.write_bytes(content)

    return output_path
