"""
Tests for Knowledge Base REST API endpoints.
"""
import io

from fastapi.testclient import TestClient

from app.main import app
from app.rag import document_loader

client = TestClient(app)


def test_get_knowledge_base_stats():
    res = client.get("/knowledge-base/stats")
    assert res.status_code == 200
    data = res.json()
    assert "documents" in data
    assert "chunks" in data
    assert "sources" in data
    assert data["documents"] >= 1


def test_list_knowledge_base_documents():
    res = client.get("/knowledge-base/documents")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "documents" in data
    assert data["total"] >= 1
    filenames = [d["filename"] for d in data["documents"]]
    assert "company_handbook.md" in filenames


def test_upload_document_invalid_extension():
    fake_file = io.BytesIO(b"binary executable payload")
    res = client.post(
        "/knowledge-base/upload",
        files={"file": ("malicious.exe", fake_file, "application/octet-stream")},
    )
    assert res.status_code == 400
    assert "Unsupported file type" in res.json()["detail"]


def test_upload_document_valid():
    test_filename = "test_policy_doc.md"
    test_file_path = document_loader.KNOWLEDGE_BASE_DIR / test_filename
    if test_file_path.exists():
        test_file_path.unlink()

    content = b"# Remote Work Policy\nEmployees may work remotely with manager approval.\n"
    file_obj = io.BytesIO(content)

    try:
        res = client.post(
            "/knowledge-base/upload",
            files={"file": (test_filename, file_obj, "text/markdown")},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert test_filename in data["message"]
        assert test_file_path.exists()
    finally:
        if test_file_path.exists():
            test_file_path.unlink()

