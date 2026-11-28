import contextvars
import shutil
from datetime import datetime
from pathlib import Path

# Base workspace directory (user-facing files only —
# the AI agent cannot access the app's own source code or escape sandbox)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
WORKSPACE_DIR = PROJECT_ROOT / "workspace"
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

# ContextVar for per-user workspace isolation
current_key_hash: contextvars.ContextVar[str] = contextvars.ContextVar("current_key_hash", default="dev_default")


def set_current_key_hash(key_hash: str):
    """Sets the caller's key hash in contextvars for per-user workspace isolation."""
    return current_key_hash.set(key_hash or "dev_default")


def get_current_key_hash() -> str:
    """Gets the caller's key hash from contextvars."""
    return current_key_hash.get() or "dev_default"


def get_workspace_dir() -> Path:
    """
    Returns the sandboxed workspace directory for the current caller.
    Each API key gets workspace/<first 16 chars of key_hash>/.
    Created on first use.
    """
    raw_hash = current_key_hash.get() or "dev_default"
    subfolder = raw_hash[:16]
    user_workspace = WORKSPACE_DIR / subfolder
    user_workspace.mkdir(parents=True, exist_ok=True)

    # Seed initial datasets for dev_default if present in base workspace
    if subfolder == "dev_default":
        for seed_file in ["monthly_sales.csv", "operations_tasks.csv"]:
            base_seed = WORKSPACE_DIR / seed_file
            target_seed = user_workspace / seed_file
            if base_seed.exists() and not target_seed.exists():
                try:
                    shutil.copy2(base_seed, target_seed)
                except Exception:
                    pass

    return user_workspace


# Files that AI is NOT allowed to access
SENSITIVE_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "secrets.json",
}

# Maximum file size allowed for read/write operations (1 MB)
MAX_FILE_BYTES = 1024 * 1024


def safe_workspace_path(path_str: str) -> Path:
    """
    Validates that a path is safe and strictly contained within the user's workspace.
    Rejects:
    - Empty paths
    - Absolute paths (leading slashes, Windows drive letters, Path.is_absolute())
    - Path traversal attacks (..)
    - Sandbox root paths (., ./)
    - Symlinks that escape the user's workspace
    - Sensitive configuration / secret files
    """
    if not path_str or not str(path_str).strip():
        raise ValueError("Invalid path: path cannot be empty.")

    clean_str = str(path_str).strip()

    # Reject explicit absolute paths
    if (
        clean_str.startswith("/")
        or clean_str.startswith("\\")
        or Path(clean_str).is_absolute()
        or (len(clean_str) > 1 and clean_str[1] == ":")
    ):
        raise PermissionError("Access Denied: Absolute paths are not permitted.")

    # Cross-platform normalization: reject .. path traversal attempts regardless of \ or /
    normalized_str = clean_str.replace("\\", "/")
    parts = [p for p in normalized_str.split("/") if p and p != "."]
    if ".." in normalized_str.split("/"):
        raise PermissionError("Access Denied: Path escapes the sandboxed workspace.")

    # Sandbox root guard: refuse direct access/deletion/rename of workspace root (.)
    if normalized_str in (".", "./", ".\\") or not parts:
        raise PermissionError("Access Denied: Sandbox root directory cannot be modified or accessed directly.")

    ws = get_workspace_dir()
    resolved_workspace = ws.resolve()
    target_path = ws / normalized_str
    resolved_target = target_path.resolve()

    # Reject direct references that resolve to the sandbox root itself
    if resolved_target == resolved_workspace:
        raise PermissionError("Access Denied: Sandbox root directory cannot be modified or accessed directly.")

    # Check path traversal
    if not resolved_target.is_relative_to(resolved_workspace):
        raise PermissionError("Access Denied: Path escapes the sandboxed workspace.")

    # Check for symlink escapes along all components
    curr = target_path
    while curr != ws and curr.parent != curr:
        if curr.is_symlink():
            if not curr.resolve().is_relative_to(resolved_workspace):
                raise PermissionError("Access Denied: Symlink escapes workspace boundary.")
        curr = curr.parent

    # Check sensitive files
    if resolved_target.name in SENSITIVE_FILES or target_path.name in SENSITIVE_FILES:
        raise PermissionError("Access Denied: Access to sensitive system file is forbidden.")

    return resolved_target


def list_workspace_files():
    """
    Lists all files and folders in the workspace.
    """
    files = []
    ws = get_workspace_dir()
    resolved_workspace = ws.resolve()
    for item in ws.iterdir():
        if item.name.startswith("."):
            continue
        if item.name in ["venv", "__pycache__"]:
            continue
        if item.is_symlink():
            try:
                if not item.resolve().is_relative_to(resolved_workspace):
                    continue
            except Exception:
                continue
        item_type = "Directory" if item.is_dir() else "File"
        files.append(f"- {item.name} ({item_type})")
    return "\n".join(files)


def read_workspace_file(filename: str):
    """
    Reads a file from the workspace, capped at 1 MB.
    """
    try:
        target_path = safe_workspace_path(filename)
        if not target_path.exists():
            return "File not found."
        if target_path.is_dir():
            return "Cannot read a directory."
        if target_path.stat().st_size > MAX_FILE_BYTES:
            return f"Error: File '{filename}' exceeds maximum allowed size of 1 MB."

        with open(target_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except (PermissionError, ValueError):
        return "Access Denied."
    except Exception as e:
        return f"Error: {str(e)}"


def write_workspace_file(filename: str, content: str):
    """
    Creates or overwrites a file, capped at 1 MB.
    """
    try:
        content_bytes = len(content.encode("utf-8"))
        if content_bytes > MAX_FILE_BYTES:
            return "Error: Content exceeds maximum allowed file size of 1 MB."

        target_path = safe_workspace_path(filename)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"Successfully wrote '{filename}'."
    except (PermissionError, ValueError):
        return "Access Denied."
    except Exception as e:
        return f"Error: {str(e)}"


def append_workspace_file(filename: str, content: str):
    """
    Appends text to a file. Creates the file if it doesn't exist. Capped at 1 MB total.
    """
    try:
        target_path = safe_workspace_path(filename)
        current_size = target_path.stat().st_size if target_path.exists() else 0
        content_bytes = len(content.encode("utf-8"))
        if current_size + content_bytes > MAX_FILE_BYTES:
            return "Error: File size after append would exceed 1 MB limit."

        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "a", encoding="utf-8") as f:
            f.write(content)

        return f"Successfully appended to '{filename}'."
    except (PermissionError, ValueError):
        return "Access Denied."
    except Exception as e:
        return f"Error: {str(e)}"


def delete_workspace_file(filename: str):
    """
    Deletes a file from the workspace.
    """
    try:
        target_path = safe_workspace_path(filename)
        if not target_path.exists():
            return "File not found."
        if target_path.is_dir():
            return "Cannot delete a directory."

        target_path.unlink()
        return f"Successfully deleted '{filename}'."
    except (PermissionError, ValueError):
        return "Access Denied."
    except Exception as e:
        return f"Error: {str(e)}"


def create_workspace_folder(foldername: str):
    """
    Creates a folder in the workspace.
    """
    try:
        target_path = safe_workspace_path(foldername)
        target_path.mkdir(parents=True, exist_ok=True)
        return f"Successfully created folder '{foldername}'."
    except (PermissionError, ValueError):
        return "Access Denied."
    except Exception as e:
        return f"Error: {str(e)}"


def delete_workspace_folder(foldername: str):
    """
    Deletes an empty folder from the workspace.
    """
    try:
        target_path = safe_workspace_path(foldername)
        if not target_path.exists():
            return "Folder not found."
        if not target_path.is_dir():
            return "This is not a folder."

        target_path.rmdir()
        return f"Successfully deleted folder '{foldername}'."
    except (PermissionError, ValueError):
        return "Access Denied."
    except OSError:
        return "Folder is not empty."
    except Exception as e:
        return f"Error: {str(e)}"


def rename_workspace_item(old_name: str, new_name: str):
    """
    Renames a file or folder in the workspace.
    """
    try:
        old_path = safe_workspace_path(old_name)
        new_path = safe_workspace_path(new_name)

        if not old_path.exists():
            return "Source not found."

        old_path.rename(new_path)
        return f"Successfully renamed '{old_name}' to '{new_name}'."
    except (PermissionError, ValueError):
        return "Access Denied."
    except Exception as e:
        return f"Error: {str(e)}"


def move_workspace_item(source: str, destination: str):
    """
    Moves a file or folder to another location within workspace.
    """
    try:
        source_path = safe_workspace_path(source)
        destination_path = safe_workspace_path(destination)

        if not source_path.exists():
            return "Source not found."

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), str(destination_path))
        return f"Successfully moved '{source}' to '{destination}'."
    except (PermissionError, ValueError):
        return "Access Denied."
    except Exception as e:
        return f"Error: {str(e)}"


def copy_workspace_item(source: str, destination: str):
    """
    Copies a file or folder within workspace.
    """
    try:
        source_path = safe_workspace_path(source)
        destination_path = safe_workspace_path(destination)

        if not source_path.exists():
            return "Source not found."

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.is_dir():
            shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
        else:
            if source_path.stat().st_size > MAX_FILE_BYTES:
                return "Error: File exceeds maximum allowed size of 1 MB."
            shutil.copy2(source_path, destination_path)

        return f"Successfully copied '{source}' to '{destination}'."
    except (PermissionError, ValueError):
        return "Access Denied."
    except Exception as e:
        return f"Error: {str(e)}"


def workspace_tree():
    """
    Displays the workspace tree.
    """
    lines = []
    ws = get_workspace_dir()
    resolved_workspace = ws.resolve()
    for path in sorted(ws.rglob("*")):
        if path.name.startswith(".") or "venv" in path.parts or "__pycache__" in path.parts:
            continue
        if path.is_symlink():
            try:
                if not path.resolve().is_relative_to(resolved_workspace):
                    continue
            except Exception:
                continue
        level = len(path.relative_to(ws).parts)
        indent = "    " * (level - 1)
        prefix = "📁" if path.is_dir() else "📄"
        lines.append(f"{indent}{prefix} {path.name}")
    return "\n".join(lines)


def workspace_summary():
    """
    Returns project statistics.
    """
    files = 0
    folders = 0
    extensions = {}
    ws = get_workspace_dir()
    resolved_workspace = ws.resolve()

    for path in ws.rglob("*"):
        if path.name.startswith(".") or "venv" in path.parts or "__pycache__" in path.parts:
            continue
        if path.is_symlink():
            try:
                if not path.resolve().is_relative_to(resolved_workspace):
                    continue
            except Exception:
                continue
        if path.is_dir():
            folders += 1
        else:
            files += 1
            ext = path.suffix.lower()
            extensions[ext] = extensions.get(ext, 0) + 1

    result = [f"Folders: {folders}", f"Files: {files}", "", "File Types:"]
    for ext, count in sorted(extensions.items()):
        name = ext if ext else "[no extension]"
        result.append(f"{name}: {count}")

    return "\n".join(result)


def get_file_information(filename: str):
    """
    Returns file information.
    """
    try:
        target = safe_workspace_path(filename)
        if not target.exists():
            return "File not found."

        stat = target.stat()
        ws = get_workspace_dir()
        return {
            "name": target.name,
            "relative_path": str(target.relative_to(ws.resolve())),
            "absolute_path": str(target),
            "size_bytes": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    except (PermissionError, ValueError):
        return "Access Denied."
    except Exception as e:
        return str(e)


def count_workspace_files():
    """
    Counts files and folders.
    """
    files = 0
    folders = 0
    ws = get_workspace_dir()
    resolved_workspace = ws.resolve()
    for item in ws.rglob("*"):
        if item.name.startswith(".") or "venv" in item.parts or "__pycache__" in item.parts:
            continue
        if item.is_symlink():
            try:
                if not item.resolve().is_relative_to(resolved_workspace):
                    continue
            except Exception:
                continue
        if item.is_file():
            files += 1
        else:
            folders += 1

    return {"files": files, "folders": folders}
