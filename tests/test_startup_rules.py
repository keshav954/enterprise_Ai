"""
Tests for Task 3: Safe API Key and Environment Startup Rules.
"""
import pytest

from app.config.settings import Settings
from app.main import validate_startup_security


def test_production_refuses_empty_key():
    """In production, missing or empty API key must raise RuntimeError."""
    s = Settings(ENV="production", APP_API_KEY="", GEMINI_API_KEY="")
    with pytest.raises(RuntimeError, match="Production mode requires APP_API_KEY"):
        validate_startup_security(s)


def test_production_refuses_non_development_open_access():
    """In non-development environments (e.g. staging), open access must be rejected."""
    s = Settings(ENV="staging", APP_API_KEY="", GEMINI_API_KEY="")
    with pytest.raises(RuntimeError, match="Open access .* is forbidden in 'staging' mode"):
        validate_startup_security(s)


def test_production_refuses_short_key():
    """In production, API keys shorter than 24 characters must raise RuntimeError."""
    s = Settings(ENV="production", APP_API_KEY="short-secret-key-1234", GEMINI_API_KEY="")
    assert len("short-secret-key-1234") < 24
    with pytest.raises(RuntimeError, match="Production API key must be at least 24 characters long"):
        validate_startup_security(s)


def test_production_refuses_placeholders():
    """In production, keys containing placeholder patterns must raise RuntimeError."""
    placeholders = [
        "your_api_key_here_12345678901234",
        "please_change_me_before_production_now",
        "an_example_api_key_that_is_long_enough",
        "super_secret_api_key_value_1234567890",
    ]
    for ph in placeholders:
        s = Settings(ENV="production", APP_API_KEY=ph, GEMINI_API_KEY="")
        with pytest.raises(RuntimeError, match="Insecure placeholder API key detected in production"):
            validate_startup_security(s)


def test_production_accepts_strong_key():
    """In production, a 24+ character non-placeholder key must pass validation cleanly."""
    valid_key = "k8Z_9pL2xVw7bNm4qR1sT3uY6cE0wA5jD"
    assert len(valid_key) >= 24
    s = Settings(ENV="production", APP_API_KEY=valid_key, GEMINI_API_KEY="")
    # Should not raise
    validate_startup_security(s)


def test_development_logs_warning_for_open_access(caplog):
    """In development, open access is permitted but logs a loud warning."""
    import logging
    s = Settings(ENV="development", APP_API_KEY="", GEMINI_API_KEY="")
    with caplog.at_level(logging.WARNING):
        validate_startup_security(s)
    assert any("running with open access" in record.message for record in caplog.records)


def test_development_logs_warning_for_insecure_keys(caplog):
    """In development, placeholder or short keys log warnings without raising exceptions."""
    import logging
    s = Settings(ENV="development", APP_API_KEY="your_secret_api_key_here", GEMINI_API_KEY="")
    with caplog.at_level(logging.WARNING):
        validate_startup_security(s)
    assert any("placeholder pattern" in record.message for record in caplog.records)
