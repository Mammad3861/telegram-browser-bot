import json
import logging
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock


logger = logging.getLogger(__name__)
_store_lock = RLock()
SUPPORTED_LANGUAGES = {"en", "fa"}


@dataclass(frozen=True)
class UserPreference:
    user_id: int
    language: str
    updated_at: str


def load_preferences(path: Path) -> list[UserPreference]:
    with _store_lock:
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Could not load user preferences; using defaults: exception_type=%s",
                type(exc).__name__,
            )
            return []

    raw_users = payload.get("users", []) if isinstance(payload, dict) else []
    preferences: list[UserPreference] = []
    for item in raw_users:
        if not isinstance(item, dict):
            continue
        try:
            user_id = int(item["user_id"])
            language = str(item["language"])
            updated_at = str(item["updated_at"])
        except (KeyError, TypeError, ValueError):
            continue
        if language not in SUPPORTED_LANGUAGES:
            continue
        preferences.append(UserPreference(user_id, language, updated_at))
    return preferences


def save_preferences(path: Path, preferences: list[UserPreference]) -> None:
    with _store_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        payload = {"users": [asdict(preference) for preference in preferences]}
        temporary.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        temporary.replace(path)


def get_user_language(path: Path, user_id: int, default: str = "en") -> str:
    for preference in load_preferences(path):
        if preference.user_id == user_id:
            return preference.language
    return default


def set_user_language(path: Path, user_id: int, language: str) -> UserPreference:
    if language not in SUPPORTED_LANGUAGES:
        raise ValueError("Unsupported language")
    with _store_lock:
        preferences = load_preferences(path)
        updated = UserPreference(
            user_id=user_id,
            language=language,
            updated_at=datetime.now(UTC).isoformat(),
        )
        remaining = [item for item in preferences if item.user_id != user_id]
        remaining.append(updated)
        save_preferences(path, remaining)
        return updated

