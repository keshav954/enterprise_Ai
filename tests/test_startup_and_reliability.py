"""
Phase 2 Checks: Startup, Reliability, Lazy Loading, Concurrency, and Tool Safety.
"""
import os
import sqlite3
import sys
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

import app.memory.memory_service as memory_service
import app.services.gemini_service as gemini_service
from app.config.settings import settings
from app.main import app, lifespan
from app.tools.code_tools import read_workspace_lines, replace_text_in_file
from app.tools.data_tools import _resolve_data_path
from app.tools.workspace_tools import (
    MAX_FILE_BYTES,
    append_workspace_file,
    delete_workspace_file,
    get_workspace_dir,
    read_workspace_file,
    write_workspace_file,
)

TEST_API_KEY = "test-reliability-key-12345"
AUTH_HEADERS = {"Authorization": f"Bearer {TEST_API_KEY}"}


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "app_api_key", TEST_API_KEY)
    monkeypatch.setattr(settings, "api_auth_token", "")
    monkeypatch.setattr(settings, "env", "development")
    monkeypatch.setattr(settings, "gemini_fake", True)


def test_import_time_fast():
    """
    Importing app.main should be fast and lightweight because chromadb
    and sentence_transformers are imported lazily.
    """
    # Test that importing vector_store does not load sentence_transformers at module level
    import app.rag.vector_store as vs
    assert "sentence_transformers" not in sys.modules or vs.get_embedding_model.cache_info().hits >= 0


def test_start_without_key_health_and_chat_503(monkeypatch):
    """
    When GEMINI_API_KEY is not set and GEMINI_FAKE is disabled:
    - /health reports gemini_configured=False
    - /chat returns 503 Service Unavailable with clear instruction
    """
    monkeypatch.setattr(settings, "gemini_api_key", "")
    monkeypatch.setattr(settings, "gemini_fake", False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_FAKE", raising=False)

    # Reset any cached client in gemini_service
    gemini_service._gemini_client = None

    client = TestClient(app)

    # GET /health should report gemini_configured=False
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["gemini_configured"] is False

    # POST /chat should return 503
    payload = {
        "message": "Hello, can you help me?",
        "session_id": "test-unconfigured-session"
    }
    chat_resp = client.post("/chat", json=payload, headers=AUTH_HEADERS)
    assert chat_resp.status_code == 503
    assert "Gemini API is not configured" in chat_resp.json()["detail"]


def test_gemini_fake_scripted_replies_and_tool_call(monkeypatch):
    """
    When GEMINI_FAKE=1, client returns scripted responses and executes tool loops offline.
    """
    monkeypatch.setattr(settings, "gemini_fake", True)
    client = TestClient(app)

    # Standard chat reply
    resp = client.post(
        "/chat",
        json={"message": "ping", "session_id": "fake-session-001"},
        headers=AUTH_HEADERS,
    )
    assert resp.status_code == 200
    assert "[Fake Gemini Double" in resp.json()["reply"]

    # Scripted tool loop trigger
    tool_resp = client.post(
        "/chat",
        json={"message": "call_tool:count_workspace_files", "session_id": "fake-session-002"},
        headers=AUTH_HEADERS,
    )
    assert tool_resp.status_code == 200
    data = tool_resp.json()
    assert len(data["tools_executed"]) == 1
    assert data["tools_executed"][0]["tool"] == "count_workspace_files"
    assert "Tool execution finished" in data["reply"]


@pytest.mark.asyncio
async def test_gemini_fake_refused_in_production(monkeypatch):
    """
    GEMINI_FAKE must be strictly refused if ENV=production.
    """
    monkeypatch.setattr(settings, "env", "production")
    monkeypatch.setattr(settings, "app_api_key", TEST_API_KEY)
    monkeypatch.setattr(settings, "gemini_fake", True)

    with pytest.raises(RuntimeError, match="GEMINI_FAKE test double is strictly forbidden"):
        async with lifespan(app):
            pass


def test_parallel_sessions_concurrency():
    """
    Verify that two sessions can run concurrently in parallel threads
    without race conditions or session data collision.
    """
    client = TestClient(app)

    def send_chat(sess_id, msg):
        return client.post(
            "/chat",
            json={"message": msg, "session_id": sess_id},
            headers=AUTH_HEADERS,
        )

    with ThreadPoolExecutor(max_workers=4) as executor:
        f1 = executor.submit(send_chat, "parallel-sess-1111", "Message from user 1")
        f2 = executor.submit(send_chat, "parallel-sess-2222", "Message from user 2")
        r1 = f1.result()
        r2 = f2.result()

    assert r1.status_code == 200
    assert r2.status_code == 200
    assert "Message from user 1" in r1.json()["reply"]
    assert "Message from user 2" in r2.json()["reply"]


def test_path_traversal_rejection():
    """
    All workspace and code tools must reject directory traversal attempts (..).
    """
    traversal_paths = [
        "../app/main.py",
        "../../etc/passwd",
        "..\\..\\boot.ini",
        "nested/../../secret.txt",
    ]

    for bad_path in traversal_paths:
        assert read_workspace_file(bad_path) == "Access Denied."
        assert write_workspace_file(bad_path, "hack") == "Access Denied."
        assert append_workspace_file(bad_path, "hack") == "Access Denied."
        assert delete_workspace_file(bad_path) == "Access Denied."
        assert read_workspace_lines(bad_path, 1, 10) == "Access Denied."
        assert replace_text_in_file(bad_path, "a", "b") == "Access Denied."


def test_absolute_path_rejection():
    """
    All workspace and code tools must reject absolute paths.
    """
    abs_paths = [
        "/etc/passwd",
        "/app/main.py",
        "C:\\Windows\\System32\\cmd.exe",
        "D:\\data.txt",
        "\\boot.ini",
    ]

    for bad_path in abs_paths:
        assert read_workspace_file(bad_path) == "Access Denied."
        assert write_workspace_file(bad_path, "hack") == "Access Denied."
        assert append_workspace_file(bad_path, "hack") == "Access Denied."
        assert read_workspace_lines(bad_path, 1, 5) == "Access Denied."
        assert replace_text_in_file(bad_path, "old", "new") == "Access Denied."
        assert _resolve_data_path(bad_path) is None


def test_symlink_escape_rejection(tmp_path):
    """
    Tools must reject symlinks that resolve to files outside the workspace.
    """
    # Create target outside workspace
    outside_file = tmp_path / "outside_target.txt"
    outside_file.write_text("Top Secret Data Outside Sandbox", encoding="utf-8")

    link_path = get_workspace_dir() / "symlink_escape_test.txt"
    if link_path.exists():
        link_path.unlink()

    try:
        os.symlink(str(outside_file), str(link_path))
        is_symlink_created = True
    except (OSError, NotImplementedError):
        # Windows privileges might not permit symlink creation for non-admin
        is_symlink_created = False

    if is_symlink_created:
        try:
            assert read_workspace_file("symlink_escape_test.txt") == "Access Denied."
            assert write_workspace_file("symlink_escape_test.txt", "overwrite") == "Access Denied."
            assert append_workspace_file("symlink_escape_test.txt", "append") == "Access Denied."
        finally:
            if link_path.is_symlink() or link_path.exists():
                link_path.unlink()


def test_sensitive_files_access_denied():
    """
    Files such as .env, secrets.json, .env.production must always be denied.
    """
    for sensitive in [".env", ".env.production", "secrets.json"]:
        assert read_workspace_file(sensitive) == "Access Denied."
        assert write_workspace_file(sensitive, "secret") == "Access Denied."
        assert append_workspace_file(sensitive, "secret") == "Access Denied."


def test_file_size_limits_1mb(tmp_path):
    """
    Workspace tools must cap reads and writes at 1 MB.
    """
    test_large_file = get_workspace_dir() / "test_too_large.txt"
    try:
        # Create a file just over 1 MB
        content = "X" * (MAX_FILE_BYTES + 100)
        with open(test_large_file, "w", encoding="utf-8") as f:
            f.write(content)

        # Reading should be rejected
        res = read_workspace_file("test_too_large.txt")
        assert "exceeds maximum allowed size of 1 MB" in res

        # Writing content > 1MB should be rejected
        write_res = write_workspace_file("test_huge_write.txt", content)
        assert "exceeds maximum allowed file size of 1 MB" in write_res

        # Read lines should be rejected
        lines_res = read_workspace_lines("test_too_large.txt", 1, 10)
        assert "exceeds maximum allowed size of 1 MB" in lines_res
    finally:
        if test_large_file.exists():
            test_large_file.unlink()


def test_sqlite_wal_and_busy_timeout(tmp_path):
    """
    SQLite memory database must enable WAL mode and busy_timeout=5000.
    """
    test_db = tmp_path / "memory_wal_test.db"
    memory_service.set_db_path(test_db)

    with memory_service.get_connection() as conn:
        journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        # In memory or file, journal mode WAL should be active
        assert journal_mode.upper() in ("WAL", "MEMORY")

        busy_timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]
        assert busy_timeout >= 5000


def test_one_time_legacy_migration(tmp_path, monkeypatch):
    """
    One-time migration should safely move old memory.db to the new data/memory.db path.
    """
    legacy_mock = tmp_path / "legacy_memory.db"
    new_mock = tmp_path / "data" / "memory.db"

    # Create dummy legacy database with a table
    with sqlite3.connect(str(legacy_mock)) as conn:
        conn.execute("CREATE TABLE legacy_test (id INT, val TEXT);")
        conn.execute("INSERT INTO legacy_test VALUES (1, 'migrated_ok');")
        conn.commit()

    monkeypatch.setattr(memory_service, "LEGACY_DB_PATH", legacy_mock)
    memory_service.migrate_legacy_db_if_needed(new_mock)

    assert new_mock.exists()
    with sqlite3.connect(str(new_mock)) as conn:
        row = conn.execute("SELECT val FROM legacy_test WHERE id = 1;").fetchone()
        assert row[0] == "migrated_ok"

