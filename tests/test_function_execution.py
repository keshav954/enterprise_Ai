from unittest.mock import MagicMock
from app.services.gemini_service import TOOL_MAP, execute_tool_call, MAX_TOOL_LOOPS
from app.tools.company_tools import get_company_info, count_workspace_files


def test_tool_map_registration():
    assert len(TOOL_MAP) == 25
    assert "get_company_info" in TOOL_MAP
    assert "count_workspace_files" in TOOL_MAP
    assert "list_python_files" in TOOL_MAP


def test_execute_tool_call_valid():
    call_mock = MagicMock()
    call_mock.name = "get_company_info"
    call_mock.args = {}

    res = execute_tool_call(call_mock)
    assert "Enterprise AI Corp Information" in res


def test_execute_tool_call_with_args():
    call_mock = MagicMock()
    call_mock.name = "count_workspace_files"
    call_mock.args = {}

    res = execute_tool_call(call_mock)
    assert "'files':" in res or "files" in res


def test_execute_tool_call_unregistered():
    call_mock = MagicMock()
    call_mock.name = "non_existent_tool"
    call_mock.args = {}

    res = execute_tool_call(call_mock)
    assert "Error: Tool 'non_existent_tool' is not registered." in res


def test_max_tool_loops_constant():
    assert MAX_TOOL_LOOPS == 5
