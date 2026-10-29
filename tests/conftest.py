"""
Shared pytest fixtures for Enterprise AI Employee tests.
"""
import os
import tempfile
from pathlib import Path

import pytest

from app.memory import memory_service


@pytest.fixture(autouse=True)
def _isolate_memory(tmp_path):
    """
    Redirect the SQLite memory database to a temp file for every test
    so tests never mutate production data and never leak state between runs.
    """
    db_file = tmp_path / "test_memory.db"
    memory_service.set_db_path(db_file)
    yield
    # Cleanup happens automatically when tmp_path is deleted
