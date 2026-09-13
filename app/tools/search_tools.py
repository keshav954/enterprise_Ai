from app.tools.workspace_tools import WORKSPACE_DIR, SENSITIVE_FILES


def search_workspace_files(keyword: str):
    """
    Searches for files and folders by name.
    """
    try:
        matches = []
        keyword = keyword.lower()
        for path in WORKSPACE_DIR.rglob("*"):
            if path.name.startswith(".") or "venv" in path.parts or "__pycache__" in path.parts:
                continue
            if keyword in path.name.lower():
                if path.is_dir():
                    matches.append(f"Directory: {path.relative_to(WORKSPACE_DIR)}")
                else:
                    matches.append(f"File: {path.relative_to(WORKSPACE_DIR)}")

        if not matches:
            return "No matching files found."
        return "\n".join(matches)
    except Exception as e:
        return f"Error: {str(e)}"


def search_text_in_workspace(text: str):
    """
    Searches for text inside all workspace files.
    """
    try:
        matches = []
        for path in WORKSPACE_DIR.rglob("*"):
            if not path.is_file() or path.name in SENSITIVE_FILES:
                continue
            if path.name.startswith(".") or "venv" in path.parts or "__pycache__" in path.parts:
                continue

            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    for line_number, line in enumerate(f, start=1):
                        if text.lower() in line.lower():
                            matches.append(
                                f"{path.relative_to(WORKSPACE_DIR)} (Line {line_number}): {line.strip()}"
                            )
            except Exception:
                continue

        if not matches:
            return "No matching text found."
        return "\n".join(matches)
    except Exception as e:
        return f"Error: {str(e)}"


def search_workspace_text(text: str):
    """
    Searches for text in all files within the workspace and outputs line references.
    """
    results = []
    try:
        for file in WORKSPACE_DIR.rglob("*"):
            if not file.is_file() or file.name in SENSITIVE_FILES:
                continue
            if file.name.startswith(".") or "venv" in file.parts or "__pycache__" in file.parts:
                continue

            try:
                with open(file, "r", encoding="utf-8", errors="replace") as f:
                    for line_number, line in enumerate(f, start=1):
                        if text.lower() in line.lower():
                            relative = file.relative_to(WORKSPACE_DIR)
                            results.append(f"{relative} : Line {line_number}\n{line.strip()}")
            except Exception:
                continue

        if not results:
            return f"No matches found for '{text}'."
        return "\n\n".join(results)
    except Exception as e:
        return f"Error: {str(e)}"


def find_workspace_files(pattern: str):
    """
    Finds files whose names contain the given pattern.
    """
    try:
        matches = []
        for item in WORKSPACE_DIR.rglob("*"):
            if not item.is_file() or item.name in SENSITIVE_FILES:
                continue
            if item.name.startswith(".") or "venv" in item.parts or "__pycache__" in item.parts:
                continue
            if pattern.lower() in item.name.lower():
                matches.append(str(item.relative_to(WORKSPACE_DIR)))

        if not matches:
            return f"No files found matching '{pattern}'."
        return "\n".join(matches)
    except Exception as e:
        return f"Error: {str(e)}"
