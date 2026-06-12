import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.core.cookies import domain_matches, normalize_domain
from app.core.encryption import decrypt_text, encrypt_text


def _storage_root() -> Path:
    return Path(get_settings().session_storage_dir)


def _session_path(user_id: int, domain: str) -> Path:
    normalized = normalize_domain(domain)
    return _storage_root() / str(user_id) / f"{normalized}.json"


def save_cookies(user_id: int, domain: str, cookies_json: str) -> None:
    settings = get_settings()
    normalized = normalize_domain(domain)
    path = _session_path(user_id, normalized)
    path.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).isoformat()
    created_at = now
    if path.exists():
        try:
            created_at = json.loads(path.read_text("utf-8")).get("created_at", now)
        except (OSError, json.JSONDecodeError):
            created_at = now
    record = {
        "user_id": user_id,
        "domain": normalized,
        "encrypted_cookies": encrypt_text(cookies_json, settings.cookie_encryption_key),
        "created_at": created_at,
        "updated_at": now,
        "user_agent": None,
    }
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(record, separators=(",", ":")), encoding="utf-8")
    temporary.replace(path)


def load_cookies(user_id: int, domain: str) -> list[dict[str, Any]]:
    settings = get_settings()
    path = _session_path(user_id, domain)
    if not path.exists():
        return []
    record = json.loads(path.read_text("utf-8"))
    if record.get("user_id") != user_id:
        return []
    plain_text = decrypt_text(record["encrypted_cookies"], settings.cookie_encryption_key)
    payload = json.loads(plain_text)
    return payload if isinstance(payload, list) else []


def load_cookies_for_domain(user_id: int, hostname: str) -> list[dict[str, Any]]:
    normalized = normalize_domain(hostname)
    matching = [
        domain for domain in list_sessions(user_id) if domain_matches(normalized, domain)
    ]
    if not matching:
        return []
    return load_cookies(user_id, max(matching, key=len))


def list_sessions(user_id: int) -> list[str]:
    directory = _storage_root() / str(user_id)
    if not directory.exists():
        return []
    return sorted(path.stem for path in directory.glob("*.json") if path.is_file())


def delete_session(user_id: int, domain: str) -> bool:
    path = _session_path(user_id, domain)
    if not path.exists():
        return False
    path.unlink()
    return True
