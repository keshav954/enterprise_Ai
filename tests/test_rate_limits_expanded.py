"""
Tests for Task 5: Expanded Rate Limiting, Settings Cleanup, and Deprecation Warnings.
"""
import io
import logging
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config.settings import Settings, settings
from app.main import app
from app.security.guard import reset_rate_limits, set_current_admin

client = TestClient(app)

ADMIN_KEY = "admin-secret-key-123456789012"
AUTH_HEADERS = {"Authorization": f"Bearer {ADMIN_KEY}"}


@pytest.fixture(autouse=True)
def setup_limits(monkeypatch):
    monkeypatch.setattr(settings, "env", "development")
    monkeypatch.setattr(settings, "app_api_key", ADMIN_KEY)
    monkeypatch.setattr(settings, "app_admin_keys", ADMIN_KEY)
    monkeypatch.setattr(settings, "rate_limit_per_min", 3)
    monkeypatch.setattr(settings, "rate_limit_heavy_per_min", 2)
    reset_rate_limits()
    set_current_admin(True)
    yield
    reset_rate_limits()


def test_heavy_rate_limit_upload(monkeypatch):
    """Uploading files must be limited to RATE_LIMIT_HEAVY_PER_MIN (2/min in test)."""
    from app.rag.document_loader import KNOWLEDGE_BASE_DIR

    rate_test_file = KNOWLEDGE_BASE_DIR / "rate_test.md"
    try:
        # 1st request
        res1 = client.post(
            "/knowledge-base/upload?overwrite=true",
            headers=AUTH_HEADERS,
            files={"file": ("rate_test.md", io.BytesIO(b"Data"), "text/markdown")},
        )
        assert res1.status_code == 200

        # 2nd request
        res2 = client.post(
            "/knowledge-base/upload?overwrite=true",
            headers=AUTH_HEADERS,
            files={"file": ("rate_test.md", io.BytesIO(b"Data"), "text/markdown")},
        )
        assert res2.status_code == 200

        # 3rd request -> exceeds heavy limit of 2 -> 429
        res3 = client.post(
            "/knowledge-base/upload?overwrite=true",
            headers=AUTH_HEADERS,
            files={"file": ("rate_test.md", io.BytesIO(b"Data"), "text/markdown")},
        )
        assert res3.status_code == 429
        assert "Rate limit exceeded" in res3.json()["detail"]
        assert "Retry-After" in res3.headers
        assert int(res3.headers["Retry-After"]) >= 1
    finally:
        if rate_test_file.exists():
            rate_test_file.unlink()


def test_heavy_rate_limit_run_tests():
    """Running tests must be limited to RATE_LIMIT_HEAVY_PER_MIN (2/min in test)."""
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "PASSED"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        # Request 1 & 2 succeed
        r1 = client.post("/workflows/run-tests", json={"test_target": "tests/"}, headers=AUTH_HEADERS)
        assert r1.status_code == 200
        r2 = client.post("/workflows/run-tests", json={"test_target": "tests/"}, headers=AUTH_HEADERS)
        assert r2.status_code == 200

        # Request 3 -> 429
        r3 = client.post("/workflows/run-tests", json={"test_target": "tests/"}, headers=AUTH_HEADERS)
        assert r3.status_code == 429
        assert "Retry-After" in r3.headers


def test_standard_rate_limit_analytics():
    """Analytics routes (/analyze) must enforce RATE_LIMIT_PER_MIN (3/min in test)."""
    for _ in range(3):
        r = client.post("/analytics/analyze", json={"filename": "monthly_sales.csv"}, headers=AUTH_HEADERS)
        assert r.status_code == 200

    # 4th request exceeds standard limit of 3
    r4 = client.post("/analytics/analyze", json={"filename": "monthly_sales.csv"}, headers=AUTH_HEADERS)
    assert r4.status_code == 429
    assert "Retry-After" in r4.headers


def test_standard_rate_limit_workflows():
    """Workflow routes (/plan) must enforce RATE_LIMIT_PER_MIN (3/min in test)."""
    for idx in range(3):
        r = client.post("/workflows/plan", json={"goal": f"Task goal {idx}"}, headers=AUTH_HEADERS)
        assert r.status_code == 200

    # 4th request -> 429
    r4 = client.post("/workflows/plan", json={"goal": "Extra goal"}, headers=AUTH_HEADERS)
    assert r4.status_code == 429
    assert "Retry-After" in r4.headers


def test_settings_rate_limit_alias_and_property():
    """Settings must parse RATE_LIMIT_PER_MINUTE alias and expose rate_limit_per_minute property."""
    s = Settings(RATE_LIMIT_PER_MINUTE=45, GEMINI_API_KEY="")
    assert s.rate_limit_per_min == 45
    assert s.rate_limit_per_minute == 45
    assert s.effective_rate_limit == 45


def test_api_auth_token_deprecation_warning(caplog):
    """Using API_AUTH_TOKEN must log a clear deprecation warning while still functioning."""
    with caplog.at_level(logging.WARNING, logger="app.config.settings"):
        s = Settings(API_AUTH_TOKEN="legacy-test-token-1234567890", APP_API_KEY="", GEMINI_API_KEY="")
        keys = s.api_keys
    assert keys == ["legacy-test-token-1234567890"]
    assert any("API_AUTH_TOKEN' is deprecated" in record.message for record in caplog.records)
