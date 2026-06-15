from app.config import Settings
from app.core.config_validation import validate_startup_config


def test_invalid_config_fallbacks(tmp_path) -> None:
    settings = Settings(
        _env_file=None,
        downloads_dir=str(tmp_path / "downloads"),
        search_provider="bad",
        download_mode="wild",
        command_menu_language_mode="invalid",
        content_policy_default_action="reject_everything",
    )

    validated = validate_startup_config(settings)

    assert validated.search_provider == "disabled"
    assert validated.download_mode == "safe"
    assert validated.command_menu_language_mode == "minimal"
    assert validated.content_policy_default_action == "allow"
