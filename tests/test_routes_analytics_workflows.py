"""
Tests for Analytics and Workflows REST API routes.
"""
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_list_datasets():
    res = client.get("/analytics/datasets")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert "datasets" in data
    filenames = [d["filename"] for d in data["datasets"]]
    assert "monthly_sales.csv" in filenames


def test_analyze_csv_dataset():
    res = client.post("/analytics/analyze", json={"filename": "monthly_sales.csv"})
    assert res.status_code == 200
    data = res.json()
    assert "monthly_sales.csv" in data["filename"]
    assert "Dataset Analysis" in data["analysis"]
    assert "Rows" in data["analysis"]


def test_analyze_invalid_extension():
    res = client.post("/analytics/analyze", json={"filename": "document.txt"})
    assert res.status_code == 400
    assert "Unsupported format" in res.json()["detail"]


def test_calculate_summary():
    res = client.post(
        "/analytics/calculate",
        json={
            "filename": "monthly_sales.csv",
            "group_by": "Category",
            "metric_column": "Revenue",
            "operation": "sum",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "Deterministic Aggregation" in data["result"]
    assert "Software" in data["result"]


def test_list_reports_and_charts():
    res = client.get("/analytics/reports")
    assert res.status_code == 200
    data = res.json()
    assert "reports" in data
    assert "charts" in data
    assert "total_reports" in data
    assert "total_charts" in data


def test_get_report_existing_and_missing():
    # Missing report returns 404
    missing_res = client.get("/analytics/reports/nonexistent_report_12345.md")
    assert missing_res.status_code == 404

    # Existing report returns markdown
    reports_res = client.get("/analytics/reports")
    reports = reports_res.json().get("reports", [])
    if reports:
        first_report = reports[0]["name"]
        res = client.get(f"/analytics/reports/{first_report}")
        assert res.status_code == 200


def test_get_report_path_traversal_guard():
    res = client.get("/analytics/reports/..%2F..%2Fapp%2Fmain.py")
    assert res.status_code in [400, 404]


def test_workflow_lifecycle_api():
    # 1. Create plan
    plan_res = client.post(
        "/workflows/plan",
        json={
            "goal": "Q4 Inventory Restocking and Supplier Purchase Order",
            "proposed_steps": "1. Analyze sales\n2. Filter low stock\n3. Overwrite inventory order table\n4. Verify delivery",
        },
    )
    assert plan_res.status_code == 200
    plan_data = plan_res.json()
    task_id = plan_data["task_id"]
    assert task_id.startswith("wf-")
    assert "Workflow Plan" in plan_data["plan"]

    # 2. List tasks
    list_res = client.get("/workflows/tasks")
    assert list_res.status_code == 200
    task_ids = [t["task_id"] for t in list_res.json()["tasks"]]
    assert task_id in task_ids

    # 3. Get single task
    task_res = client.get(f"/workflows/tasks/{task_id}")
    assert task_res.status_code == 200
    assert task_res.json()["task_id"] == task_id

    # 4. Request human approval
    appr_req = client.post(
        f"/workflows/tasks/{task_id}/approval-request",
        json={"action_description": "Submit purchase order of $45,000 to primary supplier"},
    )
    assert appr_req.status_code == 200
    assert "Human Approval Required" in appr_req.json()["message"]

    # 5. Grant human approval
    appr_decision = client.post(
        f"/workflows/tasks/{task_id}/approve",
        json={"approved": True},
    )
    assert appr_decision.status_code == 200
    assert "GRANTED" in appr_decision.json()["message"]

    # 6. Verify result
    verify_res = client.post(
        f"/workflows/tasks/{task_id}/verify",
        json={"verification_criteria": "PO signed and stock allocations validated"},
    )
    assert verify_res.status_code == 200
    assert "Workflow Verified" in verify_res.json()["message"]


def test_diagnose_failures_api():
    res = client.post(
        "/workflows/diagnose-failures",
        json={"test_output": "FAILED tests/test_calc.py::test_sum - AssertionError: 5 != 6"},
    )
    assert res.status_code == 200
    assert "Test Failure Diagnosis" in res.json()["diagnosis"]
