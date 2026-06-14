import json

import pytest

from app.core.content_policy import (
    DEFAULT_BLOCKED_CATEGORIES,
    POLICY_CATEGORIES,
    ContentPolicy,
    add_category_domain,
    add_domain_rule,
    apply_builtin_safety_lists,
    check_query_allowed,
    check_url_allowed,
    classify_domain,
    load_content_policy,
    normalize_domain,
    remove_category_domain,
    save_content_policy,
    update_category_rule,
)
from app.core.url_validation import URLValidationError


def test_domain_normalization() -> None:
    assert normalize_domain("HTTPS://WWW.Example.COM./path") == "example.com"


def test_parent_domain_blocking() -> None:
    policy = ContentPolicy(blocked_domains=["example.com"])

    decision = classify_domain("news.example.com", policy)

    assert decision.allowed is False
    assert decision.matched_rule == "example.com"


def test_allowlist_overrides_category_block() -> None:
    policy = ContentPolicy(
        allowed_domains=["safe.example"],
        blocked_categories=["adult"],
        category_domains={**ContentPolicy().category_domains, "adult": ["safe.example"]},
    )

    assert classify_domain("www.safe.example", policy).allowed is True


def test_explicit_blocked_domain_has_priority_over_allowed_domain() -> None:
    policy = ContentPolicy(
        blocked_domains=["example.com"], allowed_domains=["example.com"]
    )

    assert classify_domain("example.com", policy).allowed is False


def test_adult_and_crypto_are_not_blocked_by_default() -> None:
    policy = apply_builtin_safety_lists(ContentPolicy())

    assert classify_domain("www.pornhub.com", policy).allowed is True
    assert classify_domain("www.coinbase.com", policy).allowed is True
    assert "adult" not in policy.blocked_categories
    assert "crypto" not in policy.blocked_categories


def test_builtin_classification_blocks_only_configured_category() -> None:
    policy = apply_builtin_safety_lists(ContentPolicy(blocked_categories=["adult"]))

    decision = classify_domain("www.pornhub.com", policy)

    assert decision.allowed is False
    assert decision.category == "adult"


def test_gambling_category_is_configurable() -> None:
    policy = apply_builtin_safety_lists(ContentPolicy(blocked_categories=[]))
    assert classify_domain("sports.bet365.com", policy).allowed is True

    policy.blocked_categories.append("gambling")
    assert classify_domain("sports.bet365.com", policy).allowed is False


def test_category_rule_updates(tmp_path) -> None:
    path = tmp_path / "policy.json"

    assert update_category_rule(path, "adult", allow=False)
    assert "adult" in load_content_policy(path).blocked_categories
    assert update_category_rule(path, "adult", allow=False, remove=True)
    assert "adult" not in load_content_policy(path).blocked_categories
    assert update_category_rule(path, "adult", allow=True)
    assert "adult" in load_content_policy(path).allowed_categories


def test_add_remove_category_domain_and_parent_matching(tmp_path) -> None:
    path = tmp_path / "policy.json"

    assert add_category_domain(path, "crypto", "example.com")
    policy = load_content_policy(path)
    policy.blocked_categories.append("crypto")
    save_content_policy(path, policy)

    assert classify_domain("wallet.example.com", load_content_policy(path)).allowed is False
    assert remove_category_domain(path, "crypto", "example.com")
    assert classify_domain("wallet.example.com", load_content_policy(path)).allowed is True


def test_policy_blocks_search_query_by_keyword() -> None:
    policy = ContentPolicy(blocked_keywords=["blocked phrase"], allowed_keywords=["safe"])

    assert check_query_allowed("find BLOCKED phrase now", policy).allowed is False
    assert check_query_allowed("safe reference", policy).reason == "allowed_keyword"


def test_url_policy_decision_preserves_private_url_validation() -> None:
    policy = ContentPolicy(allowed_domains=["localhost"])

    with pytest.raises(URLValidationError):
        check_url_allowed("http://localhost/private", policy)


def test_corrupted_policy_json_falls_back_to_safe_defaults(tmp_path) -> None:
    path = tmp_path / "content_policy.json"
    path.write_text("{broken", encoding="utf-8")

    assert load_content_policy(path).blocked_categories == DEFAULT_BLOCKED_CATEGORIES


def test_old_policy_json_migrates_category_fields(tmp_path) -> None:
    path = tmp_path / "content_policy.json"
    path.write_text(json.dumps({
        "blocked_categories": ["adult", "gambling", "dangerous"],
        "adult_domains": ["adult.example"],
        "gambling_domains": ["bets.example"],
        "dangerous_domains": ["bad.example"],
    }), encoding="utf-8")

    policy = load_content_policy(path)

    assert policy.blocked_categories == ["adult", "gambling", "dangerous"]
    assert policy.category_domains["adult"] == ["adult.example"]
    assert policy.category_domains["gambling"] == ["bets.example"]
    assert policy.category_domains["dangerous"] == ["bad.example"]


def test_policy_store_adds_domain_atomically(tmp_path) -> None:
    path = tmp_path / "policies" / "content_policy.json"

    assert add_domain_rule(path, "example.com", allow=False, category="adult")
    policy = load_content_policy(path)

    assert policy.blocked_domains == ["example.com"]
    assert policy.category_domains["adult"] == ["example.com"]
    assert not path.with_suffix(".json.tmp").exists()


def test_all_required_categories_exist() -> None:
    assert POLICY_CATEGORIES == (
        "adult", "gambling", "crypto", "malware", "phishing", "dangerous", "media", "custom"
    )


def test_saved_policy_uses_new_schema(tmp_path) -> None:
    path = tmp_path / "policy.json"
    save_content_policy(path, ContentPolicy())

    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["enabled"] is True
    assert payload["blocked_categories"] == DEFAULT_BLOCKED_CATEGORIES
    assert payload["allowed_categories"] == []
    assert set(payload["category_domains"]) == set(POLICY_CATEGORIES)
    assert payload["allowed_keywords"] == []
    assert "adult_domains" not in payload
