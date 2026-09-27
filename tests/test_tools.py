import os
from app.tools.company_tools import get_company_info, TOOLS
from app.tools.workspace_tools import (
    read_workspace_file,
    write_workspace_file,
    delete_workspace_file,
    create_workspace_folder,
    delete_workspace_folder,
    workspace_summary,
    count_workspace_files,
)
from app.tools.search_tools import search_workspace_files, search_text_in_workspace
from app.tools.code_tools import list_python_files, replace_text_in_file, read_workspace_lines


def test_get_company_info():
    info = get_company_info()
    assert "Enterprise AI Corp" in info


def test_sensitive_file_protection():
    result = read_workspace_file(".env")
    assert result == "Access Denied."


def test_tools_aggregation():
    assert len(TOOLS) == 25
    tool_names = [tool.__name__ for tool in TOOLS]
    assert "get_company_info" in tool_names
    assert "list_workspace_files" in tool_names
    assert "search_workspace_files" in tool_names
    assert "list_python_files" in tool_names


def test_file_lifecycle():
    test_file = "test_scratch_temp.txt"
    # Write
    write_res = write_workspace_file(test_file, "Hello pytest world!")
    assert "Successfully wrote" in write_res

    # Read
    read_res = read_workspace_file(test_file)
    assert read_res == "Hello pytest world!"

    # Line read
    lines_res = read_workspace_lines(test_file, 1, 1)
    assert lines_res == "Hello pytest world!"

    # Replace
    replace_res = replace_text_in_file(test_file, "pytest", "unit test")
    assert replace_res == "Replacement completed."
    assert "unit test" in read_workspace_file(test_file)

    # Delete
    del_res = delete_workspace_file(test_file)
    assert "Successfully deleted" in del_res


def test_search_and_count():
    write_workspace_file("sample_test_file.py", "print('hello')")

    try:
        python_files = list_python_files()
        assert "sample_test_file.py" in python_files

        summary = workspace_summary()
        assert "Files:" in summary

        counts = count_workspace_files()
        assert counts["files"] > 0
    finally:
        delete_workspace_file("sample_test_file.py")