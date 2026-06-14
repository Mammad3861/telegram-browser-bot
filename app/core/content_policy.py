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

POLICY_CATEGORIES = (
    "adult",
    "gambling",
    "crypto",
    "malware",
    "phishing",
    "dangerous",
    "media",
    "custom",
)
DEFAULT_BLOCKED_CATEGORIES = ["malware", "phishing", "dangerous"]
PROTECTED_MEDIA_DOMAINS = {
    "youtube.com",
    "youtu.be",
    "spotify.com",
    "netflix.com",
    "soundcloud.com",
    "music.apple.com",
}
BUILTIN_CATEGORY_DOMAINS = {
    "adult": {"pornhub.com", "xvideos.com", "xnxx.com"},
    "gambling": {"bet365.com", "stake.com", "1xbet.com"},
    "crypto": {"coinbase.com", "binance.com", "kraken.com"},
    "media": set(PROTECTED_MEDIA_DOMAINS),
}
LEGACY_CATEGORY_FIELDS = {
    "adult_domains": "adult",
    "gambling_domains": "gambling",
    "media_domains": "media",
    "dangerous_domains": "dangerous",
}


def empty_category_domains() -> dict[str, list[str]]:
    return {category: [] for category in POLICY_CATEGORIES}


@dataclass
class ContentPolicy:
    enabled: bool = True
    default_action: str = "allow"
    blocked_categories: list[str] = field(
        default_factory=lambda: list(DEFAULT_BLOCKED_CATEGORIES)
    )
    allowed_categories: list[str] = field(default_factory=list)
    blocked_domains: list[str] = field(default_factory=list)
    allowed_domains: list[str] = field(default_factory=list)
    category_domains: dict[str, list[str]] = field(default_factory=empty_category_domains)
    blocked_keywords: list[str] = field(default_factory=list)
    allowed_keywords: list[str] = field(default_factory=list)
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    category: str | None = None
    matched_rule: str | None = None


def normalize_category(category: str) -> str:
    value = category.strip().lower()
    if value not in POLICY_CATEGORIES:
        raise ValueError("Invalid category")
    return value


def normalize_domain(domain: str) -> str:
    raw = domain.strip().lower()
    has_scheme = "://" in raw
    parsed = urlparse(raw if has_scheme else "//" + raw)
    if (
        (not has_scheme and (parsed.path not in {"", "/"} or parsed.query or parsed.fragment))
        or parsed.port
    ):
        raise ValueError("Invalid domain")
    value = (parsed.hostname or "").rstrip(".")
    if value.startswith("www."):
        value = value[4:]
    if not value or any(char.isspace() for char in value) or "." not in value:
        raise ValueError("Invalid domain")
    return value.encode("idna").decode("ascii")


def domain_matches(domain: str, rule: str) -> bool:
    return domain == rule or domain.endswith("." + rule)


def matching_category(domain: str, policy: ContentPolicy) -> tuple[str, str] | None:
    for category in POLICY_CATEGORIES:
        rule = next(
            (
                item
                for item in policy.category_domains.get(category, [])
                if domain_matches(domain, item)
            ),
            None,
        )
        if rule:
            return category, rule
    return None


def classify_domain(domain: str, policy: ContentPolicy) -> PolicyDecision:
    normalized = normalize_domain(domain)
    blocked_rule = next(
        (rule for rule in policy.blocked_domains if domain_matches(normalized, rule)), None
    )
    if blocked_rule:
        return PolicyDecision(False, "blocked_domain", matched_rule=blocked_rule)
    allowed_rule = next(
        (rule for rule in policy.allowed_domains if domain_matches(normalized, rule)), None
    )
    if allowed_rule:
        return PolicyDecision(True, "explicitly_allowed", matched_rule=allowed_rule)

    match = matching_category(normalized, policy)
    if match:
        category, rule = match
        if category in policy.allowed_categories:
            return PolicyDecision(True, "allowed_category", category, rule)
        if category in policy.blocked_categories:
            return PolicyDecision(False, "blocked_category", category, rule)

    if policy.default_action in {"block", "deny"}:
        return PolicyDecision(False, "default_block")
    return PolicyDecision(True, "default_allow")


def check_url_allowed(url: str, policy: ContentPolicy) -> PolicyDecision:
    validated = validate_url(url)
    hostname = urlparse(validated).hostname
    if not hostname:
        return PolicyDecision(False, "invalid_url")
    if not policy.enabled:
        return PolicyDecision(True, "policy_disabled")
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
    policy = apply_builtin_safety_lists(
        policy,
        settings.builtin_adult_category_enabled,
        settings.builtin_gambling_category_enabled,
        settings.builtin_crypto_category_enabled,
        settings.builtin_media_category_enabled,
    ) if settings.enable_builtin_safety_blocklist else policy
    if not check_url_allowed(validated, policy).allowed:
        raise ValueError("URL is blocked by content policy")
    return validated


def is_protected_media_domain(domain: str) -> bool:
    normalized = normalize_domain(domain)
    return any(domain_matches(normalized, rule) for rule in PROTECTED_MEDIA_DOMAINS)


def _normalized_domains(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for value in values:
        try:
            domain = normalize_domain(str(value))
        except ValueError:
            continue
        if domain not in normalized:
            normalized.append(domain)
    return normalized


def _normalized_categories(values: object, defaults: list[str]) -> list[str]:
    if not isinstance(values, list):
        return list(defaults)
    return [
        value
        for item in values
        if (value := str(item).strip().lower()) in POLICY_CATEGORIES
    ]


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

    category_domains = empty_category_domains()
    raw_category_domains = payload.get("category_domains")
    if isinstance(raw_category_domains, dict):
        for category in POLICY_CATEGORIES:
            category_domains[category] = _normalized_domains(
                raw_category_domains.get(category)
            )
    for legacy_field, category in LEGACY_CATEGORY_FIELDS.items():
        for domain in _normalized_domains(payload.get(legacy_field)):
            if domain not in category_domains[category]:
                category_domains[category].append(domain)

    return ContentPolicy(
        enabled=bool(payload.get("enabled", True)),
        default_action=str(payload.get("default_action") or default_action).lower(),
        blocked_categories=_normalized_categories(
            payload.get("blocked_categories"), DEFAULT_BLOCKED_CATEGORIES
        ),
        allowed_categories=_normalized_categories(payload.get("allowed_categories"), []),
        blocked_domains=_normalized_domains(payload.get("blocked_domains")),
        allowed_domains=_normalized_domains(payload.get("allowed_domains")),
        category_domains=category_domains,
        blocked_keywords=[
            str(value).lower()
            for value in payload.get("blocked_keywords", [])
            if str(value).strip()
        ] if isinstance(payload.get("blocked_keywords", []), list) else [],
        allowed_keywords=[
            str(value).lower()
            for value in payload.get("allowed_keywords", [])
            if str(value).strip()
        ] if isinstance(payload.get("allowed_keywords", []), list) else [],
        updated_at=str(payload.get("updated_at") or datetime.now(UTC).isoformat()),
    )


def apply_builtin_safety_lists(
    policy: ContentPolicy,
    adult: bool = True,
    gambling: bool = True,
    crypto: bool = True,
    media: bool = True,
) -> ContentPolicy:
    enabled = {"adult": adult, "gambling": gambling, "crypto": crypto, "media": media}
    for category, is_enabled in enabled.items():
        if is_enabled:
            policy.category_domains[category] = sorted(
                set(policy.category_domains.get(category, []))
                | BUILTIN_CATEGORY_DOMAINS[category]
            )
    return policy


def check_query_allowed(query: str, policy: ContentPolicy) -> PolicyDecision:
    normalized = " ".join(query.lower().split())
    blocked = next(
        (value for value in policy.blocked_keywords if value.lower() in normalized), None
    )
    if blocked:
        return PolicyDecision(False, "blocked_keyword", matched_rule=blocked)
    allowed = next(
        (value for value in policy.allowed_keywords if value.lower() in normalized), None
    )
    if allowed:
        return PolicyDecision(True, "allowed_keyword", matched_rule=allowed)
    return PolicyDecision(True, "default_allow")


def save_content_policy(path: Path, policy: ContentPolicy) -> None:
    with _lock:
        policy.updated_at = datetime.now(UTC).isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(asdict(policy), indent=2, ensure_ascii=False), encoding="utf-8"
        )
        temporary.replace(path)


def set_category_state(path: Path, category: str, state: str) -> bool:
    policy = load_content_policy(path)
    category = normalize_category(category)
    before = (tuple(policy.blocked_categories), tuple(policy.allowed_categories))
    policy.blocked_categories = [item for item in policy.blocked_categories if item != category]
    policy.allowed_categories = [item for item in policy.allowed_categories if item != category]
    if state == "blocked":
        policy.blocked_categories.append(category)
    elif state == "allowed":
        policy.allowed_categories.append(category)
    elif state != "neutral":
        raise ValueError("Invalid category state")
    changed = before != (tuple(policy.blocked_categories), tuple(policy.allowed_categories))
    if changed:
        save_content_policy(path, policy)
    return changed


def update_category_rule(
    path: Path, category: str, allow: bool, remove: bool = False
) -> bool:
    policy = load_content_policy(path)
    category = normalize_category(category)
    target = policy.allowed_categories if allow else policy.blocked_categories
    opposite = policy.blocked_categories if allow else policy.allowed_categories
    if remove:
        if category not in target:
            return False
        target.remove(category)
    else:
        if category in target and category not in opposite:
            return False
        if category not in target:
            target.append(category)
        if category in opposite:
            opposite.remove(category)
    save_content_policy(path, policy)
    return True


def add_category_domain(path: Path, category: str, domain: str) -> bool:
    policy = load_content_policy(path)
    category = normalize_category(category)
    domain = normalize_domain(domain)
    values = policy.category_domains.setdefault(category, [])
    if domain in values:
        return False
    values.append(domain)
    save_content_policy(path, policy)
    return True


def remove_category_domain(path: Path, category: str, domain: str) -> bool:
    policy = load_content_policy(path)
    category = normalize_category(category)
    domain = normalize_domain(domain)
    values = policy.category_domains.setdefault(category, [])
    if domain not in values:
        return False
    values.remove(domain)
    save_content_policy(path, policy)
    return True


def add_domain_rule(path: Path, domain: str, allow: bool, category: str | None = None) -> bool:
    policy = load_content_policy(path)
    normalized = normalize_domain(domain)
    target = policy.allowed_domains if allow else policy.blocked_domains
    changed = normalized not in target
    if changed:
        target.append(normalized)
    if not allow and category:
        category = normalize_category(category)
        values = policy.category_domains.setdefault(category, [])
        if normalized not in values:
            values.append(normalized)
            changed = True
    if changed:
        save_content_policy(path, policy)
    return changed


def remove_domain_rule(path: Path, domain: str, allow: bool) -> bool:
    policy = load_content_policy(path)
    normalized = normalize_domain(domain)
    target = policy.allowed_domains if allow else policy.blocked_domains
    changed = normalized in target
    if changed:
        target.remove(normalized)
    if not allow:
        for values in policy.category_domains.values():
            if normalized in values:
                values.remove(normalized)
                changed = True
    if changed:
        save_content_policy(path, policy)
    return changed
