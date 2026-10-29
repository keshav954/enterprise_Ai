from app.tools.workspace_tools import WORKSPACE_DIR, SENSITIVE_FILES, read_workspace_file

SKIPPED_DIR_NAMES = {"venv", "__pycache__"}


def read_multiple_workspace_files(*filenames):
    """
    Reads multiple files and returns concatenated results.
    """
    results = []
    for filename in filenames:
        results.append(f"\n===== {filename} =====\n")
        results.append(read_workspace_file(filename))
    return "\n".join(results)


def read_workspace_lines(filename: str, start: int, end: int):
    """
    Reads only selected line ranges from a file (1-indexed).
    """
    try:
        target = (WORKSPACE_DIR / filename).resolve()
        if target.name in SENSITIVE_FILES or not target.is_relative_to(WORKSPACE_DIR):
            return "Access Denied."
        if not target.exists():
            return "File not found."
        if target.is_dir():
            return "Cannot read a directory."

        with open(target, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        start_idx = max(0, start - 1)
        end_idx = min(len(lines), end)
        return "".join(lines[start_idx:end_idx])
    except Exception as e:
        return str(e)


def replace_text_in_file(filename: str, old_text: str, new_text: str):
    """
    Replaces text inside a file.
    """
    try:
        if not old_text:
            return "old_text must not be empty."

        target = (WORKSPACE_DIR / filename).resolve()
        if target.name in SENSITIVE_FILES or not target.is_relative_to(WORKSPACE_DIR):
            return "Access Denied."
        if not target.exists():
            return "File not found."
        if target.is_dir():
            return "Cannot edit a directory."

        # Strict decoding: refuse to edit files we can't read losslessly,
        # instead of silently corrupting them on write-back.
        try:
            with open(target, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            return "Cannot edit: file is not valid UTF-8 text."

        if old_text not in content:
            return "Target text to replace was not found in file."

        content = content.replace(old_text, new_text)

        with open(target, "w", encoding="utf-8") as f:
            f.write(content)

        return "Replacement completed."
    except Exception as e:
        return str(e)


def list_python_files():
    """
    Lists all Python files in the workspace.
    """
    files = []
    for file in WORKSPACE_DIR.rglob("*.py"):
        relative = file.relative_to(WORKSPACE_DIR)
        if any(part.startswith(".") or part in SKIPPED_DIR_NAMES for part in relative.parts):
            continue
        files.append(str(relative))
    return "\n".join(files)