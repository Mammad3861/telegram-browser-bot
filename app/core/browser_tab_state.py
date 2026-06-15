import json
import logging
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.core.encryption import EncryptionError, decrypt_text, encrypt_text


logger = logging.getLogger(__name__)


def tab_state_path(user_id: int, tab_id: str, root: Path | None = None) -> Path:
    base = root or Path(get_settings().browser_tab_state_dir)
    safe_tab_id = "".join(character for character in tab_id if character.isalnum())
    if not safe_tab_id:
        raise ValueError("Invalid tab ID")
    return base / str(user_id) / f"{safe_tab_id}.json"


def save_tab_storage_state(
    user_id: int,
    tab_id: str,
    storage_state: dict[str, Any],
    root: Path | None = None,
    encryption_key: str | None = None,
) -> bool:
    key = encryption_key if encryption_key is not None else get_settings().cookie_encryption_key
    if not key:
        return False
    path = tab_state_path(user_id, tab_id, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(storage_state, separators=(",", ":"), ensure_ascii=False)
    record = {"encrypted_storage_state": encrypt_text(payload, key)}
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(record, separators=(",", ":")), encoding="utf-8")
    temporary.replace(path)
    return True


def load_tab_storage_state(
    user_id: int,
    tab_id: str,
    root: Path | None = None,
    encryption_key: str | None = None,
) -> dict[str, Any] | None:
    key = encryption_key if encryption_key is not None else get_settings().cookie_encryption_key
    path = tab_state_path(user_id, tab_id, root)
    if not key or not path.exists():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        payload = json.loads(decrypt_text(record["encrypted_storage_state"], key))
    except (OSError, KeyError, json.JSONDecodeError, EncryptionError) as exc:
        logger.warning(
            "Could not load browser tab state: user_id=%s tab_id=%s exception_type=%s",
            user_id,
            tab_id,
            type(exc).__name__,
        )
        return None
    return payload if isinstance(payload, dict) else None
