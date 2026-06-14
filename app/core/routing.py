import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from threading import RLock
from urllib.parse import urlparse

from app.core.content_policy import domain_matches, normalize_domain
from app.core.url_validation import validate_url


logger = logging.getLogger(__name__)
_lock = RLock()


class RoutingError(RuntimeError):
    pass


@dataclass(frozen=True)
class RouteRule:
    domain: str
    route: str


def load_route_rules(path: Path) -> list[RouteRule]:
    with _lock:
        if not path.exists():
            return []
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning(
                "Could not load route rules; using defaults: exception_type=%s",
                type(exc).__name__,
            )
            return []
    rules: list[RouteRule] = []
    for item in payload.get("rules", []) if isinstance(payload, dict) else []:
        try:
            domain = normalize_domain(str(item["domain"]))
            route = str(item["route"]).lower()
            if route in {"default", "proxy"}:
                rules.append(RouteRule(domain, route))
        except (KeyError, TypeError, ValueError):
            continue
    return rules


def save_route_rules(path: Path, rules: list[RouteRule]) -> None:
    with _lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(
            json.dumps({"rules": [asdict(rule) for rule in rules]}, indent=2),
            encoding="utf-8",
        )
        temporary.replace(path)


def route_for_domain(domain: str, rules: list[RouteRule], fallback: str = "default") -> str:
    normalized = normalize_domain(domain)
    matches = [rule for rule in rules if domain_matches(normalized, rule.domain)]
    return max(matches, key=lambda rule: len(rule.domain)).route if matches else fallback


def route_for_url(url: str, path: Path, fallback: str = "default") -> str:
    hostname = urlparse(validate_url(url)).hostname or ""
    return route_for_domain(hostname, load_route_rules(path), fallback)


def set_route_rule(path: Path, domain: str, route: str) -> bool:
    normalized = normalize_domain(domain)
    normalized_route = route.strip().lower()
    if normalized_route not in {"default", "proxy"}:
        raise ValueError("Route must be default or proxy")
    rules = load_route_rules(path)
    changed = not any(
        rule.domain == normalized and rule.route == normalized_route for rule in rules
    )
    rules = [rule for rule in rules if rule.domain != normalized]
    rules.append(RouteRule(normalized, normalized_route))
    save_route_rules(path, rules)
    return changed


def remove_route_rule(path: Path, domain: str) -> bool:
    normalized = normalize_domain(domain)
    rules = load_route_rules(path)
    remaining = [rule for rule in rules if rule.domain != normalized]
    if len(remaining) == len(rules):
        return False
    save_route_rules(path, remaining)
    return True


def http_proxy_for_url(url: str, route: str, http_proxy: str, https_proxy: str) -> str | None:
    if route != "proxy":
        return None
    scheme = urlparse(url).scheme
    proxy = https_proxy if scheme == "https" else http_proxy
    if not proxy:
        proxy = http_proxy or https_proxy
    if not proxy:
        raise RoutingError("Proxy route is not configured")
    return proxy


def playwright_proxy_for_route(route: str, server: str) -> str | None:
    if route != "proxy":
        return None
    if not server:
        raise RoutingError("Proxy route is not configured")
    return server
