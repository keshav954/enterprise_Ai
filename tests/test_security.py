"""
Tests for security authentication guard and rate limiter.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config.settings import settings
from app.security.guard import reset_rate_limits

client = TestClient(app)


def test_auth_open_by_default():
    """When api_auth_token is empty, endpoints requiring auth are accessible."""
    settings.api_auth_token = ""
    res = client.delete("/chat/non-existent-session-id")
    # 404 because session doesn't exist, NOT 401 unauthorized
    assert res.status_code == 404


def test_auth_token_enforcement(monkeypatch):
    """When api_auth_token is set, requests without valid token get 401."""
    monkeypatch.setattr(settings, "api_auth_token", "secret-test-token-123")

    # No token provided
    res_no_token = client.delete("/chat/sample-session")
    assert res_no_token.status_code == 401

    # Wrong token provided
    res_wrong = client.delete(
        "/chat/sample-session",
        headers={"Authorization": "Bearer wrong-token"},
    )
    assert res_wrong.status_code == 401

    # Valid Bearer token
    res_bearer = client.delete(
        "/chat/sample-session",
        headers={"Authorization": "Bearer secret-test-token-123"},
    )
    # Passed auth check (returns 404 for missing session)
    assert res_bearer.status_code == 404

    # Valid X-API-Key header
    res_api_key = client.delete(
        "/chat/sample-session",
        headers={"X-API-Key": "secret-test-token-123"},
    )
    assert res_api_key.status_code == 404


def test_rate_limiter_exceeded(monkeypatch):
    """Rate limiter enforces max requests per minute."""
    reset_rate_limits()
    monkeypatch.setattr(settings, "rate_limit_per_minute", 3)

    # 3 allowed requests
    for _ in range(3):
        # We test hitting a route that has rate_limiter dependency
        # Chat might return 500 without Gemini key, but status won't be 429
        res = client.post("/chat", json={"message": "hello"})
        assert res.status_code != 429

    # 4th request must be 429 Too Many Requests
    res_blocked = client.post("/chat", json={"message": "hello"})
    assert res_blocked.status_code == 429
    assert "Rate limit exceeded" in res_blocked.json()["detail"]

    reset_rate_limits()

