from app.tools.workspace_tools import (
    MAX_FILE_BYTES,
    get_workspace_dir,
    read_workspace_file,
    safe_workspace_path,
)

SKIPPED_DIR_NAMES = {"venv", "__pycache__"}


def read_multiple_workspace_files(*filenames):
    """
    Reads multiple files and returns concatenated results.
    Each file access is validated and capped at 1 MB.
    """
    results = []
    for filename in filenames:
        results.append(f"\n===== {filename} =====\n")
        results.append(read_workspace_file(filename))
    return "\n".join(results)


def read_workspace_lines(filename: str, start: int, end: int):
    """
    Reads only selected line ranges from a file (1-indexed). Capped at 1 MB.
    """
    try:
        target = safe_workspace_path(filename)
        if not target.exists():
            return "File not found."
        if target.is_dir():
            return "Cannot read a directory."
        if target.stat().st_size > MAX_FILE_BYTES:
            return f"Error: File '{filename}' exceeds maximum allowed size of 1 MB."

        with open(target, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        start_idx = max(0, start - 1)
        end_idx = min(len(lines), end)
        return "".join(lines[start_idx:end_idx])
    except (PermissionError, ValueError):
        return "Access Denied."
    except Exception as e:
        return str(e)


def replace_text_in_file(filename: str, old_text: str, new_text: str):
    """
    Replaces text inside a file with size limits (1 MB).
    """
    try:
        if not old_text:
            return "old_text must not be empty."

        target = safe_workspace_path(filename)
        if not target.exists():
            return "File not found."
        if target.is_dir():
            return "Cannot edit a directory."
        if target.stat().st_size > MAX_FILE_BYTES:
            return f"Error: File '{filename}' exceeds maximum allowed size of 1 MB."

        # Strict decoding: refuse to edit files we can't read losslessly
        try:
            with open(target, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            return "Cannot edit: file is not valid UTF-8 text."

        if old_text not in content:
            return "Target text to replace was not found in file."

        new_content = content.replace(old_text, new_text)
        if len(new_content.encode("utf-8")) > MAX_FILE_BYTES:
            return "Error: Resulting file size would exceed 1 MB limit."

        with open(target, "w", encoding="utf-8") as f:
            f.write(new_content)

        return "Replacement completed."
    except (PermissionError, ValueError):
        return "Access Denied."
    except Exception as e:
        return str(e)


def list_python_files():
    """
    Lists all Python files in the workspace (safely skipping symlink escapes).
    """
    files = []
    ws = get_workspace_dir()
    resolved_workspace = ws.resolve()
    for file in ws.rglob("*.py"):
        if file.is_symlink():
            try:
                if not file.resolve().is_relative_to(resolved_workspace):
                    continue
            except Exception:
                continue
        relative = file.relative_to(ws)
        if any(part.startswith(".") or part in SKIPPED_DIR_NAMES for part in relative.parts):
            continue
        files.append(str(relative))
    return "\n".join(files)
