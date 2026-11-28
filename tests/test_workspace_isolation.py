"""
Tests for Task 1: Per-User Workspace Isolation and Security Boundaries.
"""
import hashlib

import pytest

from app.tools.search_tools import (
    find_workspace_files,
    search_text_in_workspace,
    search_workspace_files,
    search_workspace_text,
)
from app.tools.workspace_tools import (
    WORKSPACE_DIR,
    copy_workspace_item,
    delete_workspace_file,
    delete_workspace_folder,
    get_current_key_hash,
    get_workspace_dir,
    list_workspace_files,
    move_workspace_item,
    read_workspace_file,
    rename_workspace_item,
    safe_workspace_path,
    set_current_key_hash,
    write_workspace_file,
)


@pytest.fixture(autouse=True)
def reset_workspace_context():
    """Ensure key_hash is reset to dev_default after each test."""
    set_current_key_hash("dev_default")
    yield
    set_current_key_hash("dev_default")


def test_per_user_workspace_isolation():
    key_a = "user-a-secret-key-123456789012"
    key_b = "user-b-secret-key-123456789012"
    hash_a = hashlib.sha256(key_a.encode("utf-8")).hexdigest()
    hash_b = hashlib.sha256(key_b.encode("utf-8")).hexdigest()

    # --- User A writes a file ---
    set_current_key_hash(hash_a)
    assert get_current_key_hash() == hash_a
    ws_a = get_workspace_dir()
    assert ws_a == WORKSPACE_DIR / hash_a[:16]

    res_write_a = write_workspace_file("user_a_report.txt", "CONFIDENTIAL USER A DATA")
    assert "Successfully wrote" in res_write_a
    assert "user_a_report.txt" in list_workspace_files()
    assert read_workspace_file("user_a_report.txt") == "CONFIDENTIAL USER A DATA"

    # --- User B cannot see, read, search, move, overwrite, or delete User A's file ---
    set_current_key_hash(hash_b)
    ws_b = get_workspace_dir()
    assert ws_b == WORKSPACE_DIR / hash_b[:16]
    assert ws_a != ws_b

    # List
    files_b = list_workspace_files()
    assert "user_a_report.txt" not in files_b

    # Read
    assert read_workspace_file("user_a_report.txt") == "File not found."

    # Search
    assert "user_a_report.txt" not in search_workspace_files("user_a")
    assert "No matching text found." in search_text_in_workspace("CONFIDENTIAL USER A")
    assert "No matches found" in search_workspace_text("CONFIDENTIAL")
    assert "No files found" in find_workspace_files("user_a")

    # Path traversal attack to access User A's folder
    traversal_path = f"../{hash_a[:16]}/user_a_report.txt"
    assert read_workspace_file(traversal_path) == "Access Denied."
    assert write_workspace_file(traversal_path, "HACKED") == "Access Denied."
    assert delete_workspace_file(traversal_path) == "Access Denied."
    assert move_workspace_item(traversal_path, "stolen.txt") == "Access Denied."
    assert copy_workspace_item(traversal_path, "copied.txt") == "Access Denied."

    # Absolute path attack
    abs_path_a = str(ws_a / "user_a_report.txt")
    assert read_workspace_file(abs_path_a) == "Access Denied."
    assert write_workspace_file(abs_path_a, "HACKED") == "Access Denied."
    assert delete_workspace_file(abs_path_a) == "Access Denied."

    # Delete attempt by User B
    assert delete_workspace_file("user_a_report.txt") == "File not found."

    # User B writes their own file
    res_write_b = write_workspace_file("user_b_notes.txt", "USER B DATA")
    assert "Successfully wrote" in res_write_b
    assert "user_b_notes.txt" in list_workspace_files()

    # --- User A cannot see User B's file ---
    set_current_key_hash(hash_a)
    assert "user_b_notes.txt" not in list_workspace_files()
    assert read_workspace_file("user_b_notes.txt") == "File not found."
    assert read_workspace_file("user_a_report.txt") == "CONFIDENTIAL USER A DATA"

    # Cleanup
    delete_workspace_file("user_a_report.txt")
    set_current_key_hash(hash_b)
    delete_workspace_file("user_b_notes.txt")


def test_sandbox_root_guards():
    """Verify that root folder operations (delete '.', rename '.') are strictly refused."""
    # Attempting to delete sandbox root
    assert delete_workspace_folder(".") == "Access Denied."
    assert delete_workspace_folder("./") == "Access Denied."

    # Attempting to rename sandbox root
    assert rename_workspace_item(".", "evil_name") == "Access Denied."
    assert rename_workspace_item("./", "evil_name") == "Access Denied."

    # Attempting to rename an existing item to sandbox root
    write_workspace_file("valid_item.txt", "content")
    assert rename_workspace_item("valid_item.txt", ".") == "Access Denied."
    assert rename_workspace_item("valid_item.txt", "./") == "Access Denied."

    # safe_workspace_path directly raises PermissionError on root
    with pytest.raises(PermissionError, match="Sandbox root directory"):
        safe_workspace_path(".")
    with pytest.raises(PermissionError, match="Sandbox root directory"):
        safe_workspace_path("./")

    delete_workspace_file("valid_item.txt")


def test_sensitive_files_destination_guards():
    """Ensure SENSITIVE_FILES protection applies to destinations as well as sources."""
    write_workspace_file("clean_doc.txt", "safe text")

    # Rename into sensitive file
    for sensitive in [".env", ".env.local", "secrets.json"]:
        assert rename_workspace_item("clean_doc.txt", sensitive) == "Access Denied."
        assert move_workspace_item("clean_doc.txt", sensitive) == "Access Denied."
        assert copy_workspace_item("clean_doc.txt", sensitive) == "Access Denied."

    delete_workspace_file("clean_doc.txt")


def test_dev_default_isolation():
    """Verify unauthenticated / dev_default mode uses workspace/dev_default/."""
    set_current_key_hash("dev_default")
    ws_dev = get_workspace_dir()
    assert ws_dev == WORKSPACE_DIR / "dev_default"
    assert ws_dev.exists()
