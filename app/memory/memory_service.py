import sqlite3
from pathlib import Path
from typing import Dict, List, Any, Optional

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "memory.db"
_current_db_path: Path = DEFAULT_DB_PATH


def set_db_path(db_path: Path):
    """
    Sets a custom database path (useful for testing).
    """
    global _current_db_path
    _current_db_path = Path(db_path)
    init_db()


def get_connection() -> sqlite3.Connection:
    """
    Returns a new SQLite connection with auto-commit.
    """
    _current_db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_current_db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """
    Initializes the messages table and index.
    """
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_id ON messages(session_id);
        """)
        conn.commit()


# Initialize database on module load
init_db()


def save_message(session_id: str, role: str, text: str):
    """
    Saves a message turn to SQLite persistent history.
    """
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO messages (session_id, role, text) VALUES (?, ?, ?)",
            (session_id, role, text)
        )
        conn.commit()


def get_history(session_id: str) -> List[Dict[str, Any]]:
    """
    Retrieves history for a given session from SQLite.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT role, text FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        )
        rows = cursor.fetchall()
        return [{"role": row["role"], "text": row["text"]} for row in rows]


def clear_history(session_id: str) -> bool:
    """
    Clears history for a session from SQLite.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            "DELETE FROM messages WHERE session_id = ?",
            (session_id,)
        )
        conn.commit()
        return cursor.rowcount > 0


def get_stored_sessions() -> List[str]:
    """
    Returns all distinct session IDs stored in SQLite, ordered by most recent message.
    """
    with get_connection() as conn:
        cursor = conn.execute(
            "SELECT session_id FROM messages GROUP BY session_id ORDER BY MAX(id) DESC"
        )
        rows = cursor.fetchall()
        return [row["session_id"] for row in rows]