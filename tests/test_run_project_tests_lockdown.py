"""
Tests for Task 4: Lock down run_project_tests and /workflows/run-tests.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.config.settings import settings
from app.main import app
from app.security.guard import set_current_admin
from app.tools.workflow_tools import MAX_TEST_OUTPUT_CHARS, run_project_tests

client = TestClient(app)

ADMIN_KEY = "admin-secret-key-123456789012"
USER_KEY = "regular-user-key-123456789012"


@pytest.fixture(autouse=True)
def setup_test_auth(monkeypatch):
    monkeypatch.setattr(settings, "env", "development")
    monkeypatch.setattr(settings, "app_api_key", f"{ADMIN_KEY},{USER_KEY}")
    monkeypatch.setattr(settings, "app_admin_keys", ADMIN_KEY)
    set_current_admin(True)
    yield
    set_current_admin(True)


def test_reject_flags_and_options():
    """Any test target starting with '-' must be strictly refused."""
    for option in ["--co", "-p evil", "-s", "--collect-only", "-k test"]:
        res = run_project_tests(option)
        assert "Access Denied" in res
        assert "Options and flags are not permitted" in res


def test_reject_absolute_paths():
    """Absolute paths must be refused."""
    for abs_path in ["/etc/passwd", "/tests/test_api.py", "C:/Windows", "C:\\tests\\test_api.py"]:
        res = run_project_tests(abs_path)
        assert "Access Denied" in res


def test_reject_path_traversal():
    """Paths containing '..' segments must be refused."""
    for traversal in ["../", "tests/../app", "tests/../../", "..\\tests"]:
        res = run_project_tests(traversal)
        assert "Access Denied" in res


def test_reject_paths_outside_tests_dir():
    """Paths resolving outside <project>/tests/ must be refused."""
    for outside in ["app", "app/main.py", "workspace", "run.py"]:
        res = run_project_tests(outside)
        assert "Access Denied" in res
        assert "inside the tests/ directory" in res


def test_allowed_path_executes():
    """An allowed path resolving inside tests/ executes successfully."""
    # Use mock to avoid actually spawning a full subprocess run during fast unit tests
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "1 passed in 0.05s"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        res = run_project_tests("tests/test_smoke.py")
        assert "Pytest Execution Results (PASSED)" in res
        assert "1 passed in 0.05s" in res
        mock_run.assert_called_once()


def test_output_capping_at_8000_chars():
    """Returned output must be capped at 8,000 characters."""
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 1
        mock_proc.stdout = "X" * 12000
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        res = run_project_tests("tests/")
        assert f"output exceeded {MAX_TEST_OUTPUT_CHARS} characters" in res
        assert len(mock_proc.stdout) > MAX_TEST_OUTPUT_CHARS


def test_tool_admin_enforcement():
    """AI tool run_project_tests must reject non-admin callers."""
    set_current_admin(False)
    res = run_project_tests("tests/")
    assert "Access Denied" in res
    assert "administrator privileges" in res

    set_current_admin(True)
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "PASSED"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc
        res_admin = run_project_tests("tests/")
        assert "Pytest Execution Results" in res_admin


def test_route_admin_enforcement():
    """POST /workflows/run-tests must return 403 for non-admin and 200 for admin."""
    user_headers = {"Authorization": f"Bearer {USER_KEY}"}
    admin_headers = {"Authorization": f"Bearer {ADMIN_KEY}"}

    # Non-admin forbidden
    res_user = client.post("/workflows/run-tests", json={"test_target": "tests/"}, headers=user_headers)
    assert res_user.status_code == 403
    assert "Admin privileges required" in res_user.json()["detail"]

    # Admin allowed
    with patch("subprocess.run") as mock_run:
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "PASSED"
        mock_proc.stderr = ""
        mock_run.return_value = mock_proc

        res_admin = client.post("/workflows/run-tests", json={"test_target": "tests/"}, headers=admin_headers)
        assert res_admin.status_code == 200
        assert "Pytest Execution Results" in res_admin.json()["result"]
