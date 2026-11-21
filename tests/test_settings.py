"""
Unit tests for application configuration settings.
"""
from app.config.settings import Settings


def test_settings_default_values(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("MEMORY_DB_PATH", raising=False)
    monkeypatch.delenv("APP_API_KEY", raising=False)
    monkeypatch.delenv("API_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_FAKE", raising=False)
    monkeypatch.delenv("ENV", raising=False)

    s = Settings(
        _env_file=None,
    )
    assert s.gemini_model == "gemini-2.5-flash"
    assert s.memory_db_path == "data/memory.db"
    assert s.max_message_chars == 4000
    assert s.host == "0.0.0.0"
    assert s.port == 8000
    assert s.api_keys == []
    assert s.effective_rate_limit == 30


def test_settings_multiple_api_keys_parsing():
    s = Settings(
        _env_file=None,
        APP_API_KEY="key1, key2,  key3 , ",
        API_AUTH_TOKEN="",
    )
    assert s.api_keys == ["key1", "key2", "key3"]


def test_settings_legacy_auth_token_fallback():
    s = Settings(
        _env_file=None,
        APP_API_KEY="",
        API_AUTH_TOKEN="legacy_token_abc",
    )
    assert s.api_keys == ["legacy_token_abc"]


def test_settings_custom_rate_limit():
    s = Settings(
        _env_file=None,
        RATE_LIMIT_PER_MIN=60,
    )
    assert s.effective_rate_limit == 60


def test_settings_allowed_origins_parsing():
    s = Settings(
        _env_file=None,
        ALLOWED_ORIGINS="https://example.com, https://app.example.com",
    )
    origins = [o.strip() for o in s.allowed_origins.split(",") if o.strip()]
    assert origins == ["https://example.com", "https://app.example.com"]

