from instagram_saves_engine.config import Settings


def test_config_validation_missing_env_vars() -> None:
    settings = Settings()
    missing = settings.missing_for_sync()
    assert "NOTION_TOKEN" in missing
    assert "INSTAGRAM_SESSIONID" in missing
    assert settings.presence_report()["NOTION_TOKEN"] == "<missing>"
