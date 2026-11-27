"""
Shared pytest fixtures for Enterprise AI Employee tests.
"""
import pytest

from app.config.settings import settings
from app.memory import memory_service


@pytest.fixture(autouse=True)
def _isolate_test_environment(monkeypatch, tmp_path):
    """
    Redirect SQLite memory database to a temp file and isolate settings for every test
    so tests never mutate production data, never leak state, and run predictably.
    """
    db_file = tmp_path / "test_memory.db"
    memory_service.set_db_path(db_file)

    # Defaults for deterministic, offline testing
    monkeypatch.setattr(settings, "env", "development")
    monkeypatch.setattr(settings, "gemini_fake", True)
    monkeypatch.setenv("GEMINI_FAKE", "1")
    monkeypatch.setattr(settings, "app_api_key", "")
    monkeypatch.delenv("APP_API_KEY", raising=False)
