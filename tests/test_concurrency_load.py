"""
Load and Concurrency Test: 20 parallel /chat requests.
Verifies thread safety, SQLite WAL concurrency, session dictionary locking,
and error-free responses under concurrent load.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from fastapi.testclient import TestClient

from app.config.settings import settings
from app.main import app

AUTH_KEY = "concurrency-load-key"
AUTH_HEADERS = {"Authorization": f"Bearer {AUTH_KEY}"}


@pytest.fixture(autouse=True)
def configure_concurrency_env(monkeypatch):
    monkeypatch.setattr(settings, "app_api_key", AUTH_KEY)
    monkeypatch.setattr(settings, "gemini_fake", True)
    monkeypatch.setattr(settings, "env", "development")
    # Set high rate limit for load test
    monkeypatch.setattr(settings, "rate_limit_per_min", 200)
    monkeypatch.setattr(settings, "rate_limit_per_minute", 200)


def test_twenty_parallel_chat_calls():
    """
    Executes 20 concurrent /chat calls across separate sessions.
    Every call must succeed with HTTP 200 and return a valid scripted reply.
    """
    client = TestClient(app)
    num_requests = 20

    def send_single_chat(index: int):
        sess_id = f"load-session-{index:04d}"
        payload = {
            "message": f"Hello from concurrent worker {index}",
            "session_id": sess_id,
        }
        resp = client.post("/chat", json=payload, headers=AUTH_HEADERS)
        return index, resp.status_code, resp.json()

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(send_single_chat, i) for i in range(num_requests)]
        for f in as_completed(futures):
            results.append(f.result())

    assert len(results) == num_requests

    # Verify all 20 calls succeeded
    for idx, status_code, body in results:
        assert status_code == 200, f"Worker {idx} failed with {status_code}: {body}"
        assert "reply" in body
        assert f"concurrent worker {idx}" in body["reply"]
        assert body["session_id"] == f"load-session-{idx:04d}"

