"""
Comprehensive unit tests to maximize test coverage across workspace tools,
search tools, code tools, data tools, agent service, and knowledge base.
"""
import pytest

import app.rag.vector_store as vector_store
from app.rag.rag_service import knowledge_base_stats, rebuild_knowledge_base, search_knowledge_base
from app.services.agent_service import run_agent
from app.tools.code_tools import (
    list_python_files,
    read_multiple_workspace_files,
    read_workspace_lines,
    replace_text_in_file,
)
from app.tools.data_tools import (
    analyze_csv_file,
    analyze_excel_file,
    calculate_data_summary,
    create_data_chart,
    generate_analysis_report,
)
from app.tools.search_tools import (
    find_workspace_files,
    search_text_in_workspace,
    search_workspace_files,
    search_workspace_text,
)
from app.tools.workspace_tools import (
    append_workspace_file,
    copy_workspace_item,
    count_workspace_files,
    create_workspace_folder,
    delete_workspace_file,
    delete_workspace_folder,
    get_file_information,
    get_workspace_dir,
    list_workspace_files,
    move_workspace_item,
    read_workspace_file,
    rename_workspace_item,
    workspace_summary,
    workspace_tree,
    write_workspace_file,
)
from tests.test_rag import MockEmbeddingModel


@pytest.fixture(autouse=True)
def clean_workspace():
    # Setup test file in current user's workspace
    ws = get_workspace_dir()
    test_file = ws / "cov_test.txt"
    test_file.write_text("Line 1: Alpha\nLine 2: Beta target\nLine 3: Gamma\n", encoding="utf-8")
    test_py = ws / "cov_test.py"
    test_py.write_text("print('python test')", encoding="utf-8")
    yield
    # Cleanup
    for f in [test_file, test_py]:
        if f.exists():
            f.unlink()


def test_search_tools_comprehensive():
    # Search by filename
    res1 = search_workspace_files("cov_test")
    assert "cov_test.txt" in res1
    assert "No matching files" in search_workspace_files("nonexistent_random_xyz")

    # Search text
    res2 = search_text_in_workspace("Beta target")
    assert "Line 2" in res2
    assert "No matching text" in search_text_in_workspace("not_there_12345")

    # Search workspace text references
    res3 = search_workspace_text("Alpha")
    assert "cov_test.txt" in res3
    assert "No matches found" in search_workspace_text("not_there_67890")

    # Find files pattern
    res4 = find_workspace_files("cov_test")
    assert "cov_test.txt" in res4
    assert "No files found" in find_workspace_files("nonexistent_pattern_111")


def test_workspace_inspection_and_folder_tools():
    # List files
    files = list_workspace_files()
    assert "cov_test.txt" in files

    # Tree & summary
    tree = workspace_tree()
    assert "cov_test.txt" in tree
    summary = workspace_summary()
    assert "Files:" in summary

    # Counts
    counts = count_workspace_files()
    assert counts["files"] >= 1

    # File info
    info = get_file_information("cov_test.txt")
    assert isinstance(info, dict)
    assert info["name"] == "cov_test.txt"
    assert info["size_bytes"] > 0
    assert get_file_information("nonexistent.txt") == "File not found."

    # Create & delete folder
    assert "Successfully created" in create_workspace_folder("cov_folder")
    assert "Successfully deleted" in delete_workspace_folder("cov_folder")
    assert "Folder not found" in delete_workspace_folder("nonexistent_folder")


def test_workspace_file_operations():
    # Read, write, append, rename, copy, move, delete
    assert "Line 1" in read_workspace_file("cov_test.txt")
    assert read_workspace_file("nonexistent.txt") == "File not found."

    # Write & append
    assert "Successfully wrote" in write_workspace_file("cov_temp.txt", "initial content\n")
    assert "Successfully appended" in append_workspace_file("cov_temp.txt", "appended line\n")
    assert "appended line" in read_workspace_file("cov_temp.txt")

    # Copy
    assert "Successfully copied" in copy_workspace_item("cov_temp.txt", "cov_copy.txt")
    assert read_workspace_file("cov_copy.txt") == read_workspace_file("cov_temp.txt")

    # Move
    assert "Successfully moved" in move_workspace_item("cov_copy.txt", "cov_moved.txt")
    assert read_workspace_file("cov_copy.txt") == "File not found."
    assert "initial content" in read_workspace_file("cov_moved.txt")

    # Rename
    assert "Successfully renamed" in rename_workspace_item("cov_moved.txt", "cov_renamed.txt")
    assert read_workspace_file("cov_renamed.txt") != "File not found."

    # Cleanup
    delete_workspace_file("cov_temp.txt")
    delete_workspace_file("cov_renamed.txt")


def test_code_tools_comprehensive():
    # Read multiple files
    multi = read_multiple_workspace_files("cov_test.txt")
    assert "===== cov_test.txt =====" in multi
    assert "Beta target" in multi

    # Read lines
    lines = read_workspace_lines("cov_test.txt", 1, 2)
    assert "Line 1" in lines
    assert "Line 2" in lines

    # Replace text
    res = replace_text_in_file("cov_test.txt", "Alpha", "Omega")
    assert "Replacement completed" in res
    assert "Omega" in read_workspace_file("cov_test.txt")
    assert "Target text to replace was not found" in replace_text_in_file("cov_test.txt", "NonexistentTarget", "X")
    assert "old_text must not be empty" in replace_text_in_file("cov_test.txt", "", "X")

    # List python files
    py_files = list_python_files()
    assert "cov_test.py" in py_files


def test_agent_service_run_agent(monkeypatch):
    from app.config.settings import settings
    monkeypatch.setattr(settings, "gemini_fake", True)

    # Empty message error
    err = run_agent("")
    assert err["status"] == "error"

    # Successful call
    res = run_agent("Test agent prompt", session_id="agent-cov-sess-001")
    assert res["status"] == "success"
    assert "reply" in res


def test_data_tools_charts_and_reports():
    # CSV Analysis
    csv_res = analyze_csv_file("monthly_sales.csv")
    assert "Dataset Analysis" in csv_res

    # Excel fallback test
    xls_res = analyze_excel_file("monthly_sales.csv")
    assert "Excel" in xls_res or "not found" in xls_res or "Error" in xls_res

    # Summary
    sum_res = calculate_data_summary("monthly_sales.csv", "Product_Name", "Revenue")
    assert "Deterministic Aggregation" in sum_res

    # Chart
    chart_res = create_data_chart("monthly_sales.csv", "Product_Name", "Revenue", chart_type="bar")
    assert "Successfully generated" in chart_res

    # Report
    rep_res = generate_analysis_report("monthly_sales.csv", "Executive Summary on Sales", "Confirmed strong revenue in Security Sentinel.")
    assert "Report successfully generated" in rep_res


def test_rag_service_full_mocked(monkeypatch, tmp_path):
    from app.security.guard import set_current_admin

    set_current_admin(True)
    mock_model = MockEmbeddingModel()
    monkeypatch.setattr(vector_store, "get_embedding_model", lambda: mock_model)
    monkeypatch.setattr(vector_store, "CHROMA_DIR", tmp_path / "chroma")

    # Rebuild knowledge base
    rebuild_res = rebuild_knowledge_base()
    assert "rebuilt successfully" in rebuild_res

    # Grounded search
    search_res = search_knowledge_base("annual leave vacation policy")
    assert "Citation" in search_res or "Grounded" in search_res

    # Stats
    stats = knowledge_base_stats()
    assert stats["documents"] >= 1


def test_additional_coverage_edges():
    from app.services.fake_gemini import FakeGenaiClient
    from app.tools.workspace_tools import safe_workspace_path

    # Test safe_workspace_path empty
    with pytest.raises(ValueError):
        safe_workspace_path("")

    # Test FakeGenaiClient models list
    fake_client = FakeGenaiClient()
    models = fake_client.models.list()
    assert len(models) >= 2

    # Test simulated quota error in fake chat
    chat = fake_client.chats.create("gemini-2.5-flash")
    with pytest.raises(Exception, match="RESOURCE_EXHAUSTED"):
        chat.send_message("trigger_quota_error")

    # Test delete_workspace_folder on a file
    assert "not a folder" in delete_workspace_folder("cov_test.txt")

    # Test replace_text_in_file on nonexistent file
    assert "File not found" in replace_text_in_file("cov_missing.txt", "a", "b")

    # Test read_workspace_lines on nonexistent file
    assert "File not found" in read_workspace_lines("cov_missing.txt", 1, 5)


