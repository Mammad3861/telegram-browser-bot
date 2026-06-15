import asyncio

import pytest

from app.bot import handlers
from app.config import Settings
from app.core.content_policy import ContentPolicy, save_content_policy
from app.fetchers.file_detector import is_direct_file


def test_policy_blocks_url_before_card_creation(tmp_path, monkeypatch) -> None:
    path = tmp_path / "content_policy.json"
    save_content_policy(path, ContentPolicy(blocked_domains=["example.com"]))
    settings = Settings(
        _env_file=None,
        content_policy_path=str(path),
        enable_content_policy=True,
    )
    monkeypatch.setattr(handlers, "get_settings", lambda: settings)

    class FakeMessage:
        def __init__(self) -> None:
            self.answers: list[str] = []

        async def answer(self, value: str, **kwargs) -> None:
            self.answers.append(value)

    class FailingStore:
        def create(self, *args, **kwargs):
            raise AssertionError("blocked URL session should not be created")

    message = FakeMessage()
    monkeypatch.setattr(handlers, "url_session_store", FailingStore())
    monkeypatch.setattr(handlers, "get_language", lambda user_id: "en")

    asyncio.run(handlers.create_url_card(message, 1, "https://example.com"))

    assert message.answers == ["This site is blocked by the bot content policy."]


def test_search_result_blocked_by_policy_is_skipped(tmp_path, monkeypatch) -> None:
    path = tmp_path / "content_policy.json"
    save_content_policy(path, ContentPolicy(blocked_domains=["blocked.example"]))
    settings = Settings(_env_file=None, content_policy_path=str(path))
    monkeypatch.setattr(handlers, "get_settings", lambda: settings)

    assert handlers.is_policy_allowed("https://blocked.example/result") is False
    assert handlers.is_policy_allowed("https://example.com/result") is True


def test_search_result_category_filter_is_configurable(tmp_path, monkeypatch) -> None:
    path = tmp_path / "content_policy.json"
    category_domains = ContentPolicy().category_domains
    category_domains["adult"] = ["classified.example"]
    save_content_policy(
        path,
        ContentPolicy(
            blocked_categories=[],
            category_domains=category_domains,
        ),
    )
    settings = Settings(
        _env_file=None,
        content_policy_path=str(path),
        enable_builtin_safety_blocklist=False,
    )
    monkeypatch.setattr(handlers, "get_settings", lambda: settings)

    assert handlers.is_policy_allowed("https://classified.example/result") is True

    policy = handlers.current_content_policy()
    policy.blocked_categories.append("adult")
    save_content_policy(path, policy)

    assert handlers.is_policy_allowed("https://classified.example/result") is False


def test_protected_media_page_download_is_blocked(tmp_path, monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        enable_content_policy=True,
        content_policy_path=str(tmp_path / "policy.json"),
    )
    monkeypatch.setattr(handlers, "get_settings", lambda: settings)

    for url in ("https://youtube.com/watch?v=1", "https://spotify.com/track/1"):
        try:
            handlers.validate_action_url(url, "download")
        except PermissionError as exc:
            assert str(exc) == "protected_media_download"
        else:
            raise AssertionError("protected media page download was allowed")

    with pytest.raises(PermissionError):
        handlers.validate_action_url("https://youtube.com/video.mp4", "download")


def test_direct_file_url_remains_allowed(tmp_path, monkeypatch) -> None:
    settings = Settings(
        _env_file=None,
        enable_content_policy=True,
        content_policy_path=str(tmp_path / "policy.json"),
    )
    monkeypatch.setattr(handlers, "get_settings", lambda: settings)

    assert is_direct_file("https://example.com/report.pdf")
    assert handlers.validate_action_url(
        "https://example.com/report.pdf", "download"
    ) == "https://example.com/report.pdf"


def test_policy_i18n_messages_exist() -> None:
    from app.bot.i18n import TEXTS

    for key in (
        "content_policy_blocked",
        "protected_media_download",
        "proxy_not_configured",
        "media_site_note",
        "policy_categories_title",
        "policy_category_crypto",
        "policy_state_neutral",
    ):
        assert key in TEXTS["en"]
        assert key in TEXTS["fa"]


def test_policy_category_command_parser_lists_supported_categories() -> None:
    assert handlers.parse_policy_category(" CRYPTO ") == "crypto"

    with pytest.raises(ValueError):
        handlers.parse_policy_category("test")

    message = handlers.text(
        "policy_invalid_category",
        "en",
        categories=", ".join(handlers.POLICY_CATEGORY_NAMES),
    )
    assert "adult" in message
    assert "crypto" in message
    assert "custom" in message


def test_persian_policy_reason_hides_internal_code() -> None:
    label = handlers.policy_reason_label("default_allow", "fa")

    assert label == "مجاز طبق پیش‌فرض"
    assert "default_allow" not in label


def test_persian_route_labels_are_human_readable() -> None:
    assert handlers.route_label("default", "fa") == "مسیر مستقیم"
    assert handlers.route_label("proxy", "fa") == "مسیر پراکسی"
