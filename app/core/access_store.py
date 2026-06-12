import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock


_store_lock = RLock()


@dataclass(frozen=True)
class AllowedUser:
    telegram_id: int
    note: str | None
    added_by: int
    created_at: str


def load_allowed_users(path: Path) -> list[AllowedUser]:
    with _store_lock:
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
    raw_users = payload.get("allowed_users", []) if isinstance(payload, dict) else []
    users: list[AllowedUser] = []
    for item in raw_users:
        if not isinstance(item, dict):
            continue
        try:
            users.append(
                AllowedUser(
                    telegram_id=int(item["telegram_id"]),
                    note=item.get("note"),
                    added_by=int(item["added_by"]),
                    created_at=str(item["created_at"]),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return users


def save_allowed_users(path: Path, users: list[AllowedUser]) -> None:
    with _store_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        payload = {"allowed_users": [asdict(user) for user in users]}
        temporary.write_text(
            json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8"
        )
        temporary.replace(path)


def add_allowed_user(
    path: Path,
    telegram_id: int,
    added_by: int,
    note: str | None = None,
) -> bool:
    with _store_lock:
        users = load_allowed_users(path)
        if any(user.telegram_id == telegram_id for user in users):
            return False
        users.append(
            AllowedUser(
                telegram_id=telegram_id,
                note=note.strip() if note and note.strip() else None,
                added_by=added_by,
                created_at=datetime.now(UTC).isoformat(),
            )
        )
        save_allowed_users(path, users)
        return True


def remove_allowed_user(path: Path, telegram_id: int) -> bool:
    with _store_lock:
        users = load_allowed_users(path)
        remaining = [user for user in users if user.telegram_id != telegram_id]
        if len(remaining) == len(users):
            return False
        save_allowed_users(path, remaining)
        return True


def is_runtime_allowed(path: Path, telegram_id: int) -> bool:
    return any(user.telegram_id == telegram_id for user in load_allowed_users(path))


def list_allowed_users(path: Path) -> list[AllowedUser]:
    return sorted(load_allowed_users(path), key=lambda user: user.created_at)
