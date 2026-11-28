"""
Shared pytest fixtures for Enterprise AI Employee tests.
"""
import shutil
from pathlib import Path

import pytest

from app.config.settings import settings
from app.memory import memory_service

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def _isolate_test_environment(monkeypatch, tmp_path):
    """
    Redirect all file-based operations, directories, and databases to tmp_path
    so tests never write to real workspace/, knowledge_base/, reports/, or data/.
    """
    # 1. Database isolation
    db_file = tmp_path / "test_memory.db"
    memory_service.set_db_path(db_file)
    monkeypatch.setattr(settings, "memory_db_path", str(db_file))

    # 2. ChromaDB isolation
    test_chroma = tmp_path / "data" / "chroma"
    test_chroma.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("app.rag.vector_store.CHROMA_DIR", test_chroma)

    # 3. Workspace isolation
    test_workspace = tmp_path / "workspace"
    test_workspace.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("app.tools.workspace_tools.WORKSPACE_DIR", test_workspace)

    # 4. Reports & charts isolation
    test_reports = tmp_path / "reports"
    test_charts = test_reports / "charts"
    test_charts.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("app.tools.data_tools.REPORTS_DIR", test_reports)
    monkeypatch.setattr("app.tools.data_tools.CHARTS_DIR", test_charts)

    # 5. Knowledge base isolation
    test_kb = tmp_path / "knowledge_base"
    test_kb.mkdir(parents=True, exist_ok=True)
    real_kb = PROJECT_ROOT / "knowledge_base"
    if real_kb.exists():
        for f in real_kb.glob("*"):
            if f.is_file() and f.name != "test_policy_doc.md":
                shutil.copy2(f, test_kb / f.name)
    monkeypatch.setattr("app.rag.document_loader.KNOWLEDGE_BASE_DIR", test_kb)
    monkeypatch.setattr("app.rag.rag_service.KNOWLEDGE_BASE_DIR", test_kb)
    monkeypatch.setattr("app.routes.knowledge_base.KNOWLEDGE_BASE_DIR", test_kb)

    # 6. Seed datasets for test workspaces from tests/fixtures
    fixtures_dir = PROJECT_ROOT / "tests" / "fixtures"
    dev_workspace = test_workspace / "dev_default"
    dev_workspace.mkdir(parents=True, exist_ok=True)
    if fixtures_dir.exists():
        for fixture_file in fixtures_dir.glob("*"):
            if fixture_file.is_file():
                shutil.copy2(fixture_file, dev_workspace / fixture_file.name)

    # 7. Defaults for deterministic, offline testing
    monkeypatch.setattr(settings, "env", "development")
    monkeypatch.setattr(settings, "gemini_fake", True)
    monkeypatch.setenv("GEMINI_FAKE", "1")
    monkeypatch.setattr(settings, "app_api_key", "")
    monkeypatch.delenv("APP_API_KEY", raising=False)
