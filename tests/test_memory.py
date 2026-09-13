import os
import tempfile
from pathlib import Path
from app.memory import memory_service


def test_memory_crud_operations():
    # Use temporary DB file
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_file = Path(tmp.name)

    try:
        memory_service.set_db_path(db_file)
        session_id = "test-session-123"

        # Initially empty
        assert memory_service.get_history(session_id) == []

        # Save messages
        memory_service.save_message(session_id, "user", "Hello AI")
        memory_service.save_message(session_id, "model", "Hello human!")

        # Retrieve history
        history = memory_service.get_history(session_id)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["text"] == "Hello AI"
        assert history[1]["role"] == "model"

        # Check stored sessions
        stored = memory_service.get_stored_sessions()
        assert session_id in stored

        # Clear history
        assert memory_service.clear_history(session_id) is True
        assert memory_service.get_history(session_id) == []
    finally:
        if db_file.exists():
            try:
                os.remove(db_file)
            except OSError:
                pass


def test_memory_persistence():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_file = Path(tmp.name)

    try:
        memory_service.set_db_path(db_file)
        session_id = "test-persist-999"

        memory_service.save_message(session_id, "user", "Persistent message")

        # Simulate fresh re-initialization with same DB file
        memory_service.set_db_path(db_file)
        history = memory_service.get_history(session_id)

        assert len(history) == 1
        assert history[0]["text"] == "Persistent message"
    finally:
        if db_file.exists():
            try:
                os.remove(db_file)
            except OSError:
                pass
