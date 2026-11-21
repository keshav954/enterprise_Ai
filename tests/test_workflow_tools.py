"""
Unit tests for AI Workflow Engine and Developer Assistant tools.
"""
from app.tools.workflow_tools import (
    approve_task_step,
    create_task_plan,
    get_task_status,
    request_task_approval,
    run_project_tests,
    summarize_test_failures,
    verify_task_result,
)


def test_workflow_lifecycle():
    # 1. Create Plan
    goal = "Analyze sales data and generate verified report"
    res_plan = create_task_plan(goal)
    assert "Workflow Plan:" in res_plan
    assert "wf-" in res_plan

    # Extract task ID
    import re
    match = re.search(r"wf-[a-f0-9]{8}", res_plan)
    assert match is not None
    task_id = match.group(0)

    # 2. Check Status
    res_status = get_task_status(task_id)
    assert "Workflow Status:" in res_status
    assert "IN_PROGRESS" in res_status

    # 3. Request Human Approval for consequential action
    res_appr = request_task_approval(task_id, "Publish external supplier purchase order")
    assert "Human Approval Required" in res_appr

    res_status_after = get_task_status(task_id)
    assert "AWAITING_APPROVAL" in res_status_after

    # 4. Grant Approval
    res_grant = approve_task_step(task_id, approved=True)
    assert "Approval GRANTED" in res_grant

    # 5. Verify Output
    res_verify = verify_task_result(task_id, "Revenue matches sum of individual line items")
    assert "Workflow Verified:" in res_verify
    assert "SUCCESS" in res_verify


def test_workflow_approval_denial():
    res_plan = create_task_plan("Dangerous action")
    import re
    task_id = re.search(r"wf-[a-f0-9]{8}", res_plan).group(0)

    request_task_approval(task_id, "Delete customer database")
    res_deny = approve_task_step(task_id, approved=False)
    assert "Approval REJECTED" in res_deny

    res_status = get_task_status(task_id)
    assert "REJECTED" in res_status


def test_run_project_tests_security_guard():
    res = run_project_tests("tests/; rm -rf /")
    assert "Access Denied" in res


def test_summarize_test_failures():
    sample_failed_output = (
        "FAILED tests/test_math.py::test_division - ZeroDivisionError: division by zero\n"
        "ERROR tests/test_db.py - OperationalError: database is locked\n"
        "1 failed, 1 error, 10 passed in 2.5s"
    )
    summary = summarize_test_failures(sample_failed_output)
    assert "Test Failure Diagnosis" in summary
    assert "ZeroDivisionError" in summary
    assert "database is locked" in summary

    # Clean output
    clean_summary = summarize_test_failures("5 passed in 0.2s")
    assert "No test failures detected" in clean_summary

