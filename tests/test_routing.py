import pytest

from app.core.routing import (
    RouteRule,
    RoutingError,
    http_proxy_for_url,
    load_route_rules,
    route_for_domain,
    set_route_rule,
)


def test_route_rule_parent_domain_matching() -> None:
    rules = [RouteRule("example.com", "proxy")]

    assert route_for_domain("cdn.example.com", rules) == "proxy"
    assert route_for_domain("example.org", rules) == "default"


def test_more_specific_route_rule_wins() -> None:
    rules = [
        RouteRule("example.com", "proxy"),
        RouteRule("direct.example.com", "default"),
    ]

    assert route_for_domain("www.direct.example.com", rules) == "default"


def test_proxy_route_missing_configuration_is_safe() -> None:
    with pytest.raises(RoutingError, match="not configured"):
        http_proxy_for_url("https://example.com", "proxy", "", "")


def test_route_rules_persist(tmp_path) -> None:
    path = tmp_path / "route_rules.json"

    assert set_route_rule(path, "example.com", "proxy")

    assert load_route_rules(path) == [RouteRule("example.com", "proxy")]
