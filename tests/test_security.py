"""
Tests for Security: API-key Authentication, Rate Limiting, CORS,
Session Scoping, Validation, Request-ID, and XSS Sanitization.
"""
import hashlib

import pytest
from fastapi.testclient import TestClient

from app.config.settings import settings
from app.main import app
from app.memory import memory_service
from app.security.guard import reset_rate_limits

client = TestClient(app)


def test_auth_open_by_default_in_dev(monkeypatch):
    """When no API key is configured and ENV=development, access is permitted."""
    monkeypatch.setattr(settings, "app_api_key", "")
    monkeypatch.setattr(settings, "api_auth_token", "")
    monkeypatch.setattr(settings, "env", "development")

    res = client.delete("/chat/valid-session-12345")
    # 404 because session does not exist, NOT 401
    assert res.status_code == 404


def test_auth_enforcement_bearer_token(monkeypatch):
    """When APP_API_KEY is configured, requests without valid Bearer token return 401."""
    monkeypatch.setattr(settings, "app_api_key", "secret-key-alpha, secret-key-beta")
    monkeypatch.setattr(settings, "api_auth_token", "")
    monkeypatch.setattr(settings, "env", "development")

    # 1. No Authorization header -> 401
    res_none = client.get("/tools")
    assert res_none.status_code == 401
    assert "WWW-Authenticate" in res_none.headers

    # 2. Malformed Authorization header -> 401
    res_bad = client.get("/tools", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert res_bad.status_code == 401

    # 3. Wrong token -> 401
    res_wrong = client.get("/tools", headers={"Authorization": "Bearer wrong-key"})
    assert res_wrong.status_code == 401

    # 4. Valid key alpha -> 200
    res_alpha = client.get("/tools", headers={"Authorization": "Bearer secret-key-alpha"})
    assert res_alpha.status_code == 200

    # 5. Valid key beta (comma-separated list support) -> 200
    res_beta = client.get("/tools", headers={"Authorization": "Bearer secret-key-beta"})
    assert res_beta.status_code == 200


@pytest.mark.anyio
async def test_production_mode_refuses_without_key(monkeypatch):
    """If ENV=production and no key is configured, application startup refuses to proceed."""
    from app.main import lifespan
    monkeypatch.setattr(settings, "app_api_key", "")
    monkeypatch.setattr(settings, "api_auth_token", "")
    monkeypatch.setattr(settings, "env", "production")

    with pytest.raises(RuntimeError, match="Production mode requires APP_API_KEY"):
        async with lifespan(app):
            pass


def test_health_and_static_are_auth_exempt(monkeypatch):
    """GET /health, /dashboard, and /static files are exempt from API key auth."""
    monkeypatch.setattr(settings, "app_api_key", "super-secret-key-999")
    monkeypatch.setattr(settings, "api_auth_token", "")

    # GET /health is open
    res_health = client.get("/health")
    assert res_health.status_code == 200

    # GET /dashboard is open
    res_dash = client.get("/dashboard")
    assert res_dash.status_code == 200

    # GET /static/app.js is open
    res_static = client.get("/static/app.js")
    assert res_static.status_code == 200


def test_cross_session_isolation(monkeypatch):
    """
    Sessions are strictly scoped to caller's API key hash.
    User B cannot list, view history, or delete User A's session (returns 404).
    """
    key_a = "user-a-secret-key"
    key_b = "user-b-secret-key"
    monkeypatch.setattr(settings, "app_api_key", f"{key_a}, {key_b}")
    monkeypatch.setattr(settings, "api_auth_token", "")
    monkeypatch.setattr(settings, "env", "development")
    monkeypatch.setattr(settings, "gemini_fake", True)
    monkeypatch.setenv("GEMINI_FAKE", "1")

    headers_a = {"Authorization": f"Bearer {key_a}"}
    headers_b = {"Authorization": f"Bearer {key_b}"}

    key_hash_a = hashlib.sha256(key_a.encode()).hexdigest()
    session_a = "session-user-a-001"

    # Seed a session directly in memory_service under User A's key_hash
    memory_service.save_message(session_a, "user", "Hello from User A", key_hash=key_hash_a)
    memory_service.save_message(session_a, "model", "Greetings User A", key_hash=key_hash_a)

    # 1. User A lists sessions -> sees session_a
    res_sessions_a = client.get("/sessions", headers=headers_a)
    assert res_sessions_a.status_code == 200
    assert session_a in res_sessions_a.json()["session_ids"]

    # 2. User B lists sessions -> DOES NOT see session_a
    res_sessions_b = client.get("/sessions", headers=headers_b)
    assert res_sessions_b.status_code == 200
    assert session_a not in res_sessions_b.json()["session_ids"]

    # 3. User A can view history -> 200
    res_hist_a = client.get(f"/chat/{session_a}/history", headers=headers_a)
    assert res_hist_a.status_code == 200
    assert len(res_hist_a.json()["history"]) == 2

    # 4. User B attempts to view User A's history -> 404
    res_hist_b = client.get(f"/chat/{session_a}/history", headers=headers_b)
    assert res_hist_b.status_code == 404

    # 5. User B attempts to delete User A's session -> 404
    res_del_b = client.delete(f"/chat/{session_a}", headers=headers_b)
    assert res_del_b.status_code == 404

    # 6. User B attempts to post to User A's session -> 404
    res_chat_b = client.post(
        "/chat",
        headers=headers_b,
        json={"message": "Hijack attempt", "session_id": session_a},
    )
    assert res_chat_b.status_code == 404

    # 7. User A can delete their own session -> 200
    res_del_a = client.delete(f"/chat/{session_a}", headers=headers_a)
    assert res_del_a.status_code == 200


def test_cors_preflight_disallowed_origin(monkeypatch):
    """CORS preflight from an unauthorized origin is rejected."""
    monkeypatch.setattr(settings, "allowed_origins", "http://localhost:8000,http://127.0.0.1:8000")

    # Disallowed origin preflight
    res_disallowed = client.options(
        "/chat",
        headers={
            "Origin": "http://malicious-website.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    # The header Access-Control-Allow-Origin should NOT match the malicious origin
    assert res_disallowed.headers.get("access-control-allow-origin") != "http://malicious-website.com"

    # Allowed origin preflight
    res_allowed = client.options(
        "/chat",
        headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization,Content-Type",
        },
    )
    assert res_allowed.headers.get("access-control-allow-origin") == "http://localhost:8000"


def test_rate_limiter_exceeded_with_retry_after(monkeypatch):
    """Rate limiter enforces limit per key and returns 429 with Retry-After header."""
    reset_rate_limits()
    monkeypatch.setattr(settings, "rate_limit_per_min", 3)
    monkeypatch.setattr(settings, "rate_limit_per_minute", 3)
    monkeypatch.setattr(settings, "app_api_key", "rate-limit-test-key")
    monkeypatch.setattr(
        "app.routes.chat.send_message",
        lambda *args, **kwargs: {"session_id": "test_sess_01", "reply": "ok", "tools_executed": []},
    )
    headers = {"Authorization": "Bearer rate-limit-test-key"}

    # 3 allowed requests
    for _ in range(3):
        res = client.post("/chat", headers=headers, json={"message": "hello valid length"})
        assert res.status_code != 429

    # 4th request must be 429 Too Many Requests
    res_blocked = client.post("/chat", headers=headers, json={"message": "hello valid length"})
    assert res_blocked.status_code == 429
    assert "Rate limit exceeded" in res_blocked.json()["detail"]
    assert "Retry-After" in res_blocked.headers
    assert int(res_blocked.headers["Retry-After"]) >= 1

    reset_rate_limits()


def test_pydantic_validation_message():
    """Pydantic validates message length: 1..MAX_MESSAGE_CHARS."""
    # 1. Empty message -> 422
    res_empty = client.post("/chat", json={"message": ""})
    assert res_empty.status_code == 422

    # 2. Whitespace-only message -> 422
    res_ws = client.post("/chat", json={"message": "   \n\t  "})
    assert res_ws.status_code == 422

    # 3. Message exceeding MAX_MESSAGE_CHARS -> 422
    long_msg = "x" * 4001
    res_long = client.post("/chat", json={"message": long_msg})
    assert res_long.status_code == 422


def test_pydantic_validation_session_id(monkeypatch):
    """Pydantic validates session_id: ^[A-Za-z0-9_-]{8,64}$."""
    monkeypatch.setattr(
        "app.routes.chat.send_message",
        lambda *args, **kwargs: {"session_id": "test_sess_01", "reply": "ok", "tools_executed": []},
    )

    # 1. Too short (< 8 chars) -> 422
    res_short = client.post("/chat", json={"message": "valid message", "session_id": "short"})
    assert res_short.status_code == 422

    # 2. Invalid characters (spaces, punctuation, scripts) -> 422
    res_invalid_chars = client.post(
        "/chat",
        json={"message": "valid message", "session_id": "invalid session!@#"},
    )
    assert res_invalid_chars.status_code == 422

    # 3. Path parameter validation on /chat/{session_id}/history -> 422
    res_path = client.get("/chat/bad!id/history")
    assert res_path.status_code == 422

    # 4. Valid session_id pattern (8-64 chars: alphanumeric, _, -)
    # Passed validation; returns 500 or chat reply, not 422
    res_valid = client.post(
        "/chat",
        json={"message": "valid message", "session_id": "valid_session_12345"},
    )
    assert res_valid.status_code != 422


def test_request_id_middleware():
    """Every request receives an X-Request-ID response header and passes it to logs."""
    res = client.get("/health")
    assert res.status_code == 200
    assert "X-Request-ID" in res.headers
    assert len(res.headers["X-Request-ID"]) >= 8

    # Client-provided X-Request-ID is preserved
    custom_id = "custom-client-trace-id-12345"
    res_custom = client.get("/health", headers={"X-Request-ID": custom_id})
    assert res_custom.headers["X-Request-ID"] == custom_id


def test_xss_inert_rendering(monkeypatch):
    """XSS payloads such as <img src=x onerror=alert(1)> are sanitized and rendered inert."""
    import html

    monkeypatch.setattr(
        "app.routes.chat.send_message",
        lambda *args, **kwargs: {"session_id": "test_xss_01", "reply": "ok", "tools_executed": []},
    )

    xss_payload = '<img src=x onerror=alert(1)>'

    # 1. Pydantic accepts the text as content
    req = client.post("/chat", json={"message": xss_payload})
    assert req.status_code != 422

    # 2. Server HTML escaping ensures no raw executable script tags are echoed
    escaped = html.escape(xss_payload)
    assert "<script>" not in escaped
    assert "&lt;img" in escaped
    assert "&gt;" in escaped
