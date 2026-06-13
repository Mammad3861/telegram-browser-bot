import json
import logging
from pathlib import Path
from threading import RLock


logger = logging.getLogger(__name__)
_store_lock = RLock()
EDITABLE_TEXT_KEYS = {"welcome", "help", "about"}
SUPPORTED_LANGUAGES = {"en", "fa"}


class BotTextValidationError(ValueError):
    def __init__(self, message: str, code: str = "invalid_text") -> None:
        super().__init__(message)
        self.code = code


def validate_text_target(key: str, language: str) -> tuple[str, str]:
    normalized_key = key.strip().lower()
    normalized_language = language.strip().lower()
    if normalized_key not in EDITABLE_TEXT_KEYS:
        raise BotTextValidationError(
            "Editable key must be welcome, help, or about", "invalid_key"
        )
    if normalized_language not in SUPPORTED_LANGUAGES:
        raise BotTextValidationError("Language must be en or fa", "invalid_language")
    return normalized_key, normalized_language


def load_bot_texts(path: Path) -> dict[str, dict[str, str]]:
    with _store_lock:
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Could not load editable bot texts; using defaults: exception_type=%s",
                type(exc).__name__,
            )
            return {}
    if not isinstance(payload, dict):
        return {}
    texts: dict[str, dict[str, str]] = {}
    for key, languages in payload.items():
        if key not in EDITABLE_TEXT_KEYS or not isinstance(languages, dict):
            continue
        valid = {
            language: value
            for language, value in languages.items()
            if language in SUPPORTED_LANGUAGES and isinstance(value, str) and value
        }
        if valid:
            texts[key] = valid
    return texts


def save_bot_texts(path: Path, texts: dict[str, dict[str, str]]) -> None:
    with _store_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(texts, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        temporary.replace(path)


def get_bot_text(path: Path, key: str, language: str) -> str | None:
    key, language = validate_text_target(key, language)
    return load_bot_texts(path).get(key, {}).get(language)


def set_bot_text(
    path: Path,
    key: str,
    language: str,
    value: str,
    max_length: int,
) -> None:
    key, language = validate_text_target(key, language)
    normalized = value.strip()
    if not normalized:
        raise BotTextValidationError("Text cannot be empty", "empty_text")
    if len(normalized) > max_length:
        raise BotTextValidationError(
            f"Text must be at most {max_length} characters", "text_too_long"
        )
    with _store_lock:
        texts = load_bot_texts(path)
        texts.setdefault(key, {})[language] = normalized
        save_bot_texts(path, texts)


def reset_bot_text(path: Path, key: str, language: str | None = None) -> bool:
    normalized_key = key.strip().lower()
    if normalized_key not in EDITABLE_TEXT_KEYS:
        raise BotTextValidationError(
            "Editable key must be welcome, help, or about", "invalid_key"
        )
    if language is not None:
        _, normalized_language = validate_text_target(normalized_key, language)
    else:
        normalized_language = None
    with _store_lock:
        texts = load_bot_texts(path)
        if normalized_key not in texts:
            return False
        if normalized_language is None:
            texts.pop(normalized_key, None)
            changed = True
        else:
            changed = texts[normalized_key].pop(normalized_language, None) is not None
            if not texts[normalized_key]:
                texts.pop(normalized_key, None)
        if changed:
            save_bot_texts(path, texts)
        return changed
