"""
Tests for Task 2: Knowledge Base Access Control & Overwrite Protection.
"""
import io

import pytest
from fastapi.testclient import TestClient

from app.config.settings import settings
from app.main import app
from app.rag import document_loader
from app.rag.rag_service import rebuild_knowledge_base
from app.security.guard import set_current_admin

client = TestClient(app)

ADMIN_KEY = "admin-secret-key-123456789012"
USER_KEY = "regular-user-key-123456789012"


@pytest.fixture(autouse=True)
def setup_keys(monkeypatch):
    monkeypatch.setattr(settings, "env", "development")
    monkeypatch.setattr(settings, "app_api_key", f"{ADMIN_KEY},{USER_KEY}")
    monkeypatch.setattr(settings, "app_admin_keys", ADMIN_KEY)
    set_current_admin(True)
    yield
    set_current_admin(True)


def test_non_admin_write_forbidden():
    """Non-admin keys must receive 403 Forbidden on upload and rebuild."""
    user_headers = {"Authorization": f"Bearer {USER_KEY}"}

    # 1. Rebuild endpoint forbidden
    res_rebuild = client.post("/knowledge-base/rebuild", headers=user_headers)
    assert res_rebuild.status_code == 403
    assert "Admin privileges required" in res_rebuild.json()["detail"]

    # 2. Upload endpoint forbidden
    file_payload = io.BytesIO(b"# Policy\nSample text")
    res_upload = client.post(
        "/knowledge-base/upload",
        headers=user_headers,
        files={"file": ("test_doc.md", file_payload, "text/markdown")},
    )
    assert res_upload.status_code == 403
    assert "Admin privileges required" in res_upload.json()["detail"]

    # 3. Read & search operations are allowed for regular users
    res_docs = client.get("/knowledge-base/documents", headers=user_headers)
    assert res_docs.status_code == 200

    res_stats = client.get("/knowledge-base/stats", headers=user_headers)
    assert res_stats.status_code == 200


def test_rebuild_tool_admin_enforcement():
    """AI tool rebuild_knowledge_base must reject non-admin callers."""
    set_current_admin(False)
    result = rebuild_knowledge_base()
    assert "Access Denied" in result
    assert "administrator privileges" in result

    set_current_admin(True)
    # When admin, tool executes build_vector_index (may succeed or rebuild)
    # We just ensure it doesn't return Access Denied
    res_admin = rebuild_knowledge_base()
    assert "Access Denied" not in res_admin


def test_upload_duplicate_without_overwrite_returns_409():
    """Uploading an existing filename without overwrite=true must return 409 Conflict."""
    admin_headers = {"Authorization": f"Bearer {ADMIN_KEY}"}
    existing_file = "company_handbook.md"
    assert (document_loader.KNOWLEDGE_BASE_DIR / existing_file).exists()

    payload = io.BytesIO(b"# Modified handbook content\nNew content.")
    res = client.post(
        "/knowledge-base/upload",
        headers=admin_headers,
        files={"file": (existing_file, payload, "text/markdown")},
    )
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"]
    assert "overwrite=true" in res.json()["detail"]


def test_upload_duplicate_with_overwrite_succeeds(tmp_path):
    """Uploading with overwrite=true by an admin replaces file and returns 200."""
    admin_headers = {"Authorization": f"Bearer {ADMIN_KEY}"}
    test_file_name = "test_overwrite_target.md"
    test_path = document_loader.KNOWLEDGE_BASE_DIR / test_file_name
    test_path.write_text("# Initial Content\nInitial text.", encoding="utf-8")

    try:
        updated_payload = io.BytesIO(b"# Updated Content\nBrand new text.")
        res = client.post(
            "/knowledge-base/upload?overwrite=true",
            headers=admin_headers,
            files={"file": (test_file_name, updated_payload, "text/markdown")},
        )
        assert res.status_code == 200
        assert "Successfully uploaded" in res.json()["message"]
        assert "Updated Content" in test_path.read_text(encoding="utf-8")
    finally:
        if test_path.exists():
            test_path.unlink()


def test_first_key_fallback_admin(monkeypatch):
    """If APP_ADMIN_KEYS is not configured, the first key in APP_API_KEY acts as admin."""
    monkeypatch.setattr(settings, "app_admin_keys", "")
    monkeypatch.setattr(settings, "app_api_key", f"primary-key-1,{USER_KEY}")

    assert settings.admin_keys == ["primary-key-1"]

    # primary-key-1 is admin -> can access rebuild
    res_admin = client.post(
        "/knowledge-base/rebuild",
        headers={"Authorization": "Bearer primary-key-1"},
    )
    assert res_admin.status_code == 200

    # USER_KEY is not admin -> receives 403
    res_user = client.post(
        "/knowledge-base/rebuild",
        headers={"Authorization": f"Bearer {USER_KEY}"},
    )
    assert res_user.status_code == 403
