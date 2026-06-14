from app.core.content_policy import (
    ContentPolicy,
    add_domain_rule,
    check_url_allowed,
    classify_domain,
    load_content_policy,
    normalize_domain,
    apply_builtin_safety_lists,
    check_query_allowed,
)


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
        adult_domains=["safe.example"],
    )

    assert classify_domain("www.safe.example", policy).allowed is True


def test_category_domain_decisions() -> None:
    policy = ContentPolicy(
        blocked_categories=["adult", "gambling", "dangerous"],
        adult_domains=["adult.example"],
        gambling_domains=["bets.example"],
        dangerous_domains=["bad.example"],
    )

    assert classify_domain("adult.example", policy).category == "adult"
    assert classify_domain("bets.example", policy).category == "gambling"
    assert classify_domain("bad.example", policy).category == "dangerous"


def test_media_category_can_be_blocked() -> None:
    policy = ContentPolicy(
        blocked_categories=["media"], media_domains=["media.example"]
    )

    decision = classify_domain("video.media.example", policy)

    assert decision.allowed is False
    assert decision.category == "media"


def test_default_block_action_blocks_unmatched_domains() -> None:
    policy = ContentPolicy(default_action="block")

    assert classify_domain("example.com", policy).allowed is False


def test_policy_blocks_search_query_by_keyword() -> None:
    policy = ContentPolicy(blocked_keywords=["blocked phrase"])

    assert check_query_allowed("find BLOCKED phrase now", policy).allowed is False


def test_builtin_adult_and_gambling_domains_are_filtered() -> None:
    policy = apply_builtin_safety_lists(ContentPolicy())

    assert classify_domain("www.pornhub.com", policy).allowed is False
    assert classify_domain("sports.bet365.com", policy).allowed is False


def test_url_policy_decision_preserves_url_validation() -> None:
    policy = ContentPolicy(blocked_domains=["example.com"])

    assert check_url_allowed("https://www.example.com/page", policy).allowed is False


def test_corrupted_policy_json_falls_back_to_defaults(tmp_path) -> None:
    path = tmp_path / "content_policy.json"
    path.write_text("{broken", encoding="utf-8")

    policy = load_content_policy(path)

    assert policy.blocked_categories == [
        "adult",
        "gambling",
        "malware",
        "phishing",
        "dangerous",
    ]


def test_policy_store_adds_domain_atomically(tmp_path) -> None:
    path = tmp_path / "policies" / "content_policy.json"

    assert add_domain_rule(path, "example.com", allow=False, category="adult")
    policy = load_content_policy(path)

    assert policy.blocked_domains == ["example.com"]
    assert policy.adult_domains == ["example.com"]
    assert not path.with_suffix(".json.tmp").exists()
