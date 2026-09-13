from pathlib import Path
from datetime import datetime
import shutil

# Project root directory
WORKSPACE_DIR = Path(__file__).resolve().parent.parent.parent

# Files that AI is NOT allowed to access
SENSITIVE_FILES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    "secrets.json",
}


def list_workspace_files():
    """
    Lists all files and folders in the workspace.
    """
    files = []
    for item in WORKSPACE_DIR.iterdir():
        if item.name.startswith("."):
            continue
        if item.name in ["venv", "__pycache__"]:
            continue
        item_type = "Directory" if item.is_dir() else "File"
        files.append(f"- {item.name} ({item_type})")
    return "\n".join(files)


def read_workspace_file(filename: str):
    """
    Reads a file from the workspace.
    """
    target_path = (WORKSPACE_DIR / filename).resolve()
    if target_path.name in SENSITIVE_FILES:
        return "Access Denied."
    if not target_path.is_relative_to(WORKSPACE_DIR):
        return "Access Denied."
    if not target_path.exists():
        return "File not found."
    if target_path.is_dir():
        return "Cannot read a directory."

    with open(target_path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()


def write_workspace_file(filename: str, content: str):
    """
    Creates or overwrites a file.
    """
    try:
        target_path = (WORKSPACE_DIR / filename).resolve()
        if target_path.name in SENSITIVE_FILES:
            return "Access Denied."
        if not target_path.is_relative_to(WORKSPACE_DIR):
            return "Access Denied."

        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)

        return f"Successfully wrote '{filename}'."
    except Exception as e:
        return f"Error: {str(e)}"


def append_workspace_file(filename: str, content: str):
    """
    Appends text to a file. Creates the file if it doesn't exist.
    """
    try:
        target_path = (WORKSPACE_DIR / filename).resolve()
        if target_path.name in SENSITIVE_FILES:
            return "Access Denied."
        if not target_path.is_relative_to(WORKSPACE_DIR):
            return "Access Denied."

        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "a", encoding="utf-8") as f:
            f.write(content)

        return f"Successfully appended to '{filename}'."
    except Exception as e:
        return f"Error: {str(e)}"


def delete_workspace_file(filename: str):
    """
    Deletes a file from the workspace.
    """
    try:
        target_path = (WORKSPACE_DIR / filename).resolve()
        if target_path.name in SENSITIVE_FILES:
            return "Access Denied."
        if not target_path.is_relative_to(WORKSPACE_DIR):
            return "Access Denied."
        if not target_path.exists():
            return "File not found."
        if target_path.is_dir():
            return "Cannot delete a directory."

        target_path.unlink()
        return f"Successfully deleted '{filename}'."
    except Exception as e:
        return f"Error: {str(e)}"


def create_workspace_folder(foldername: str):
    """
    Creates a folder in the workspace.
    """
    try:
        target_path = (WORKSPACE_DIR / foldername).resolve()
        if not target_path.is_relative_to(WORKSPACE_DIR):
            return "Access Denied."

        target_path.mkdir(parents=True, exist_ok=True)
        return f"Successfully created folder '{foldername}'."
    except Exception as e:
        return f"Error: {str(e)}"


def delete_workspace_folder(foldername: str):
    """
    Deletes an empty folder from the workspace.
    """
    try:
        target_path = (WORKSPACE_DIR / foldername).resolve()
        if not target_path.is_relative_to(WORKSPACE_DIR):
            return "Access Denied."
        if not target_path.exists():
            return "Folder not found."
        if not target_path.is_dir():
            return "This is not a folder."

        target_path.rmdir()
        return f"Successfully deleted folder '{foldername}'."
    except OSError:
        return "Folder is not empty."
    except Exception as e:
        return f"Error: {str(e)}"


def rename_workspace_item(old_name: str, new_name: str):
    """
    Renames a file or folder in the workspace.
    """
    try:
        old_path = (WORKSPACE_DIR / old_name).resolve()
        new_path = (WORKSPACE_DIR / new_name).resolve()

        if not old_path.is_relative_to(WORKSPACE_DIR) or not new_path.is_relative_to(WORKSPACE_DIR):
            return "Access Denied."
        if old_path.name in SENSITIVE_FILES or new_path.name in SENSITIVE_FILES:
            return "Access Denied."
        if not old_path.exists():
            return "Source not found."

        old_path.rename(new_path)
        return f"Successfully renamed '{old_name}' to '{new_name}'."
    except Exception as e:
        return f"Error: {str(e)}"


def move_workspace_item(source: str, destination: str):
    """
    Moves a file or folder to another location.
    """
    try:
        source_path = (WORKSPACE_DIR / source).resolve()
        destination_path = (WORKSPACE_DIR / destination).resolve()

        if not source_path.is_relative_to(WORKSPACE_DIR) or not destination_path.is_relative_to(WORKSPACE_DIR):
            return "Access Denied."
        if source_path.name in SENSITIVE_FILES:
            return "Access Denied."
        if not source_path.exists():
            return "Source not found."

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source_path), str(destination_path))
        return f"Successfully moved '{source}' to '{destination}'."
    except Exception as e:
        return f"Error: {str(e)}"


def copy_workspace_item(source: str, destination: str):
    """
    Copies a file or folder.
    """
    try:
        source_path = (WORKSPACE_DIR / source).resolve()
        destination_path = (WORKSPACE_DIR / destination).resolve()

        if not source_path.is_relative_to(WORKSPACE_DIR) or not destination_path.is_relative_to(WORKSPACE_DIR):
            return "Access Denied."
        if source_path.name in SENSITIVE_FILES:
            return "Access Denied."
        if not source_path.exists():
            return "Source not found."

        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if source_path.is_dir():
            shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
        else:
            shutil.copy2(source_path, destination_path)

        return f"Successfully copied '{source}' to '{destination}'."
    except Exception as e:
        return f"Error: {str(e)}"


def workspace_tree():
    """
    Displays the workspace tree.
    """
    lines = []
    for path in sorted(WORKSPACE_DIR.rglob("*")):
        if path.name.startswith(".") or "venv" in path.parts or "__pycache__" in path.parts:
            continue
        level = len(path.relative_to(WORKSPACE_DIR).parts)
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

    for path in WORKSPACE_DIR.rglob("*"):
        if path.name.startswith(".") or "venv" in path.parts or "__pycache__" in path.parts:
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
        target = (WORKSPACE_DIR / filename).resolve()
        if target.name in SENSITIVE_FILES or not target.is_relative_to(WORKSPACE_DIR):
            return "Access Denied."
        if not target.exists():
            return "File not found."

        stat = target.stat()
        return {
            "name": target.name,
            "relative_path": str(target.relative_to(WORKSPACE_DIR)),
            "absolute_path": str(target),
            "size_bytes": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        }
    except Exception as e:
        return str(e)


def count_workspace_files():
    """
    Counts files and folders.
    """
    files = 0
    folders = 0
    for item in WORKSPACE_DIR.rglob("*"):
        if item.name.startswith(".") or "venv" in item.parts or "__pycache__" in item.parts:
            continue
        if item.is_file():
            files += 1
        else:
            folders += 1

    return {"files": files, "folders": folders}
