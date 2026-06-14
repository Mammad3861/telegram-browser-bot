import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from urllib.parse import urlparse

from app.core.url_validation import validate_url


logger = logging.getLogger(__name__)
_lock = RLock()
DEFAULT_BLOCKED_CATEGORIES = ["adult", "gambling", "malware", "phishing", "dangerous"]
PROTECTED_MEDIA_DOMAINS = {
    "youtube.com",
    "youtu.be",
    "spotify.com",
    "netflix.com",
    "soundcloud.com",
    "music.apple.com",
}
CATEGORY_FIELDS = {
    "media": "media_domains",
    "gambling": "gambling_domains",
    "adult": "adult_domains",
    "dangerous": "dangerous_domains",
    "malware": "dangerous_domains",
    "phishing": "dangerous_domains",
}


@dataclass
class ContentPolicy:
    blocked_domains: list[str] = field(default_factory=list)
    allowed_domains: list[str] = field(default_factory=list)
    blocked_keywords: list[str] = field(default_factory=list)
    blocked_categories: list[str] = field(
        default_factory=lambda: list(DEFAULT_BLOCKED_CATEGORIES)
    )
    media_domains: list[str] = field(default_factory=list)
    gambling_domains: list[str] = field(default_factory=list)
    adult_domains: list[str] = field(default_factory=list)
    dangerous_domains: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    default_action: str = "allow"


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    category: str | None = None
    matched_rule: str | None = None


def normalize_domain(domain: str) -> str:
    raw = domain.strip().lower()
    has_scheme = "://" in raw
    parsed = urlparse(raw if has_scheme else "//" + raw)
    if (not has_scheme and (parsed.path not in {"", "/"} or parsed.query or parsed.fragment)) or parsed.port:
        raise ValueError("Invalid domain")
    value = (parsed.hostname or "").rstrip(".")
    if value.startswith("www."):
        value = value[4:]
    if not value or any(char.isspace() for char in value) or "." not in value:
        raise ValueError("Invalid domain")
    return value.encode("idna").decode("ascii")


def domain_matches(domain: str, rule: str) -> bool:
    return domain == rule or domain.endswith("." + rule)


def classify_domain(domain: str, policy: ContentPolicy) -> PolicyDecision:
    normalized = normalize_domain(domain)
    allowed_rule = next(
        (rule for rule in policy.allowed_domains if domain_matches(normalized, rule)), None
    )
    if allowed_rule:
        return PolicyDecision(True, "explicitly_allowed", matched_rule=allowed_rule)
    blocked_rule = next(
        (rule for rule in policy.blocked_domains if domain_matches(normalized, rule)), None
    )
    if blocked_rule:
        return PolicyDecision(False, "blocked_domain", matched_rule=blocked_rule)
    for category, field_name in CATEGORY_FIELDS.items():
        rules = getattr(policy, field_name)
        rule = next((item for item in rules if domain_matches(normalized, item)), None)
        if rule and category in policy.blocked_categories:
            return PolicyDecision(False, "blocked_category", category, rule)
    keyword = next(
        (item for item in policy.blocked_keywords if item.lower() in normalized), None
    )
    if keyword:
        return PolicyDecision(False, "blocked_keyword", matched_rule=keyword)
    if policy.default_action == "block":
        return PolicyDecision(False, "default_block")
    return PolicyDecision(True, "default_allow")


def check_url_allowed(url: str, policy: ContentPolicy) -> PolicyDecision:
    validated = validate_url(url)
    hostname = urlparse(validated).hostname
    if not hostname:
        return PolicyDecision(False, "invalid_url")
    return classify_domain(hostname, policy)


def validate_configured_policy(url: str) -> str:
    from app.config import get_settings

    validated = validate_url(url)
    settings = get_settings()
    if not settings.enable_content_policy:
        return validated
    policy = load_content_policy(
        Path(settings.content_policy_path), settings.content_policy_default_action
    )
    if not check_url_allowed(validated, policy).allowed:
        raise ValueError("URL is blocked by content policy")
    return validated


def is_protected_media_domain(domain: str) -> bool:
    normalized = normalize_domain(domain)
    return any(domain_matches(normalized, rule) for rule in PROTECTED_MEDIA_DOMAINS)


def load_content_policy(path: Path, default_action: str = "allow") -> ContentPolicy:
    with _lock:
        if not path.exists():
            return ContentPolicy(default_action=default_action)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Could not load content policy; using defaults: exception_type=%s",
                type(exc).__name__,
            )
            return ContentPolicy(default_action=default_action)
    if not isinstance(payload, dict):
        return ContentPolicy(default_action=default_action)
    policy = ContentPolicy(default_action=default_action)
    for field_name in (
        "blocked_domains", "allowed_domains", "blocked_keywords", "blocked_categories",
        "media_domains", "gambling_domains", "adult_domains", "dangerous_domains",
    ):
        values = payload.get(field_name)
        if isinstance(values, list):
            if field_name.endswith("_domains"):
                normalized_values = []
                for value in values:
                    try:
                        normalized_values.append(normalize_domain(str(value)))
                    except ValueError:
                        continue
                setattr(policy, field_name, normalized_values)
            else:
                setattr(
                    policy,
                    field_name,
                    [str(value).lower() for value in values if str(value).strip()],
                )
    policy.updated_at = str(payload.get("updated_at") or policy.updated_at)
    policy.default_action = str(payload.get("default_action") or default_action).lower()
    return policy


def save_content_policy(path: Path, policy: ContentPolicy) -> None:
    with _lock:
        policy.updated_at = datetime.now(UTC).isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(asdict(policy), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        temporary.replace(path)


def add_domain_rule(path: Path, domain: str, allow: bool, category: str | None = None) -> bool:
    policy = load_content_policy(path)
    normalized = normalize_domain(domain)
    target = policy.allowed_domains if allow else policy.blocked_domains
    if normalized in target:
        return False
    target.append(normalized)
    if not allow and category:
        field_name = CATEGORY_FIELDS.get(category.lower())
        if field_name and normalized not in getattr(policy, field_name):
            getattr(policy, field_name).append(normalized)
    save_content_policy(path, policy)
    return True


def remove_domain_rule(path: Path, domain: str, allow: bool) -> bool:
    policy = load_content_policy(path)
    normalized = normalize_domain(domain)
    target = policy.allowed_domains if allow else policy.blocked_domains
    changed = normalized in target
    if changed:
        target.remove(normalized)
    if not allow:
        for field_name in set(CATEGORY_FIELDS.values()):
            values = getattr(policy, field_name)
            if normalized in values:
                values.remove(normalized)
                changed = True
    if changed:
        save_content_policy(path, policy)
    return changed
