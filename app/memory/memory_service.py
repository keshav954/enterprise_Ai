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
    Initializes sessions and messages tables with caller key_hash indexing.
    """
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                key_hash TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_key_hash ON sessions(key_hash);
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                text TEXT NOT NULL,
                key_hash TEXT NOT NULL DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
        """)

        # Migration check: ensure key_hash column exists on messages if table was created earlier
        cur = conn.execute("PRAGMA table_info(messages)")
        cols = [row["name"] for row in cur.fetchall()]
        if "key_hash" not in cols:
            conn.execute("ALTER TABLE messages ADD COLUMN key_hash TEXT NOT NULL DEFAULT ''")

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_key_hash ON messages(key_hash);
        """)

        conn.commit()


# Initialize database on module load
init_db()


def save_message(session_id: str, role: str, text: str, key_hash: str = ""):
    """
    Saves a message turn to SQLite persistent history with caller scoping.
    """
    with get_connection() as conn:
        # Check or register session ownership
        cursor = conn.execute("SELECT key_hash FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO sessions (session_id, key_hash) VALUES (?, ?)",
                (session_id, key_hash)
            )
        elif key_hash and row["key_hash"] and row["key_hash"] != key_hash:
            raise PermissionError("Cross-session access denied.")

        conn.execute(
            "INSERT INTO messages (session_id, role, text, key_hash) VALUES (?, ?, ?, ?)",
            (session_id, role, text, key_hash)
        )
        conn.commit()


def get_history(session_id: str, key_hash: str = "") -> Optional[List[Dict[str, Any]]]:
    """
    Retrieves history for a given session.
    If key_hash is provided, returns None if the session does not exist or belongs
    to another caller (enforcing 404 on cross-session access).
    If key_hash is empty, returns the list of messages (empty list if none).
    """
    with get_connection() as conn:
        cursor = conn.execute("SELECT key_hash FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        if key_hash:
            if row is None or (row["key_hash"] and row["key_hash"] != key_hash):
                return None

        cursor = conn.execute(
            "SELECT role, text FROM messages WHERE session_id = ? ORDER BY id ASC",
            (session_id,)
        )
        rows = cursor.fetchall()
        return [{"role": r["role"], "text": r["text"]} for r in rows]


def clear_history(session_id: str, key_hash: str = "") -> bool:
    """
    Clears history for a session. Returns False if session does not exist or
    belongs to a different caller.
    """
    with get_connection() as conn:
        cursor = conn.execute("SELECT key_hash FROM sessions WHERE session_id = ?", (session_id,))
        row = cursor.fetchone()
        if key_hash:
            if row is None or (row["key_hash"] and row["key_hash"] != key_hash):
                return False

        cur_msg = conn.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        cur_sess = conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        conn.commit()
        return (row is not None) or (cur_msg.rowcount > 0) or (cur_sess.rowcount > 0)


def get_stored_sessions(key_hash: str = "") -> List[str]:
    """
    Returns distinct session IDs stored in SQLite, scoped to the caller's key_hash.
    """
    with get_connection() as conn:
        if key_hash:
            cursor = conn.execute(
                "SELECT session_id FROM sessions WHERE key_hash = ? ORDER BY created_at DESC",
                (key_hash,)
            )
        else:
            cursor = conn.execute(
                "SELECT session_id FROM sessions ORDER BY created_at DESC"
            )
        rows = cursor.fetchall()
        return [row["session_id"] for row in rows]
