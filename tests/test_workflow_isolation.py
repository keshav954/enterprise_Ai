"""
Tests for Task 1: Workflow Isolation and Multi-Tenant Security.
Ensures workflows are strictly scoped to the owner's key_hash and
cannot be listed, accessed, approved, or verified across tenants.
"""
import concurrent.futures
import hashlib

from fastapi.testclient import TestClient

from app.config.settings import settings
from app.main import app
from app.tools.workflow_tools import (
    _WORKFLOWS,
    approve_task_step,
    create_task_plan,
    get_task_status,
    request_task_approval,
    verify_task_result,
)
from app.tools.workspace_tools import set_current_key_hash

client = TestClient(app)

USER_A_KEY = "user-a-secret-key-123456789012"
USER_B_KEY = "user-b-secret-key-123456789012"
AUTH_A = {"Authorization": f"Bearer {USER_A_KEY}"}
AUTH_B = {"Authorization": f"Bearer {USER_B_KEY}"}


def setup_users(monkeypatch):
    monkeypatch.setattr(settings, "env", "development")
    monkeypatch.setattr(settings, "app_api_key", f"{USER_A_KEY},{USER_B_KEY}")
    monkeypatch.setattr(settings, "gemini_fake", True)


def test_workflow_cross_user_isolation(monkeypatch):
    """
    User A cannot list, read, approve, or verify User B's workflows.
    Cross-user access attempts must return HTTP 404, not 403.
    """
    setup_users(monkeypatch)

    # User A creates a plan
    res_a = client.post(
        "/workflows/plan",
        headers=AUTH_A,
        json={"goal": "User A secret engineering project"},
    )
    assert res_a.status_code == 200
    task_a = res_a.json()["task_id"]
    assert task_a.startswith("wf-")

    # User B creates a plan
    res_b = client.post(
        "/workflows/plan",
        headers=AUTH_B,
        json={"goal": "User B proprietary marketing launch"},
    )
    assert res_b.status_code == 200
    task_b = res_b.json()["task_id"]
    assert task_b.startswith("wf-")
    assert task_a != task_b

    # 1. Listing tasks: User A sees only task_a; User B sees only task_b
    list_a = client.get("/workflows/tasks", headers=AUTH_A)
    assert list_a.status_code == 200
    ids_a = [t["task_id"] for t in list_a.json()["tasks"]]
    assert task_a in ids_a
    assert task_b not in ids_a

    list_b = client.get("/workflows/tasks", headers=AUTH_B)
    assert list_b.status_code == 200
    ids_b = [t["task_id"] for t in list_b.json()["tasks"]]
    assert task_b in ids_b
    assert task_a not in ids_b

    # 2. Reading task details: cross-user reading returns 404
    read_a_by_b = client.get(f"/workflows/tasks/{task_a}", headers=AUTH_B)
    assert read_a_by_b.status_code == 404
    assert "not found" in read_a_by_b.json()["detail"].lower()

    read_b_by_a = client.get(f"/workflows/tasks/{task_b}", headers=AUTH_A)
    assert read_b_by_a.status_code == 404

    # 3. Requesting approval: cross-user request returns 404
    appr_req = client.post(
        f"/workflows/tasks/{task_a}/approval-request",
        headers=AUTH_B,
        json={"action_description": "Malicious approval injection"},
    )
    assert appr_req.status_code == 404

    # 4. Approving/rejecting: cross-user decision returns 404
    approve_by_b = client.post(
        f"/workflows/tasks/{task_a}/approve",
        headers=AUTH_B,
        json={"approved": True},
    )
    assert approve_by_b.status_code == 404

    # 5. Verifying results: cross-user verification returns 404
    verify_by_b = client.post(
        f"/workflows/tasks/{task_a}/verify",
        headers=AUTH_B,
        json={"verification_criteria": "Validate without ownership"},
    )
    assert verify_by_b.status_code == 404


def test_workflow_tools_context_isolation():
    """
    Workflow tools called directly (e.g. by AI agent) enforce key_hash boundaries.
    """
    hash_a = hashlib.sha256(USER_A_KEY.encode()).hexdigest()
    hash_b = hashlib.sha256(USER_B_KEY.encode()).hexdigest()

    # User A creates a plan via tool
    set_current_key_hash(hash_a)
    plan_a = create_task_plan("Tool-created workflow by User A")
    task_a = plan_a.task_id
    assert task_a.startswith("wf-")

    # User B switches context
    set_current_key_hash(hash_b)

    # User B cannot inspect User A's task
    status_msg = get_task_status(task_a)
    assert f"Workflow `{task_a}` not found" in status_msg
    assert task_a not in status_msg.split("Available tasks:")[1]

    # User B cannot request approval for User A's task
    appr_res = request_task_approval(task_a, "Deploy update")
    assert f"Workflow `{task_a}` not found" in appr_res

    # User B cannot approve User A's task
    grant_res = approve_task_step(task_a, approved=True)
    assert f"Workflow `{task_a}` not found" in grant_res

    # User B cannot verify User A's task
    verify_res = verify_task_result(task_a, "Verification criteria")
    assert f"Workflow `{task_a}` not found" in verify_res


def test_concurrent_plan_creation_returns_distinct_ids(monkeypatch):
    """
    Concurrent calls to create_task_plan return distinct, exact task IDs
    without any race condition from dictionary order.
    """
    setup_users(monkeypatch)

    def create_single_plan(idx: int):
        user_key = USER_A_KEY if idx % 2 == 0 else USER_B_KEY
        auth_hdr = {"Authorization": f"Bearer {user_key}"}
        res = client.post(
            "/workflows/plan",
            headers=auth_hdr,
            json={"goal": f"Concurrent task {idx} execution goal"},
        )
        assert res.status_code == 200
        data = res.json()
        return idx, data["task_id"], data["workflow"]["goal"]

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(create_single_plan, i) for i in range(16)]
        results = [f.result() for f in futures]

    task_ids = [r[1] for r in results]
    # All 16 task IDs must be unique
    assert len(set(task_ids)) == 16
    for idx, tid, goal in results:
        assert f"Concurrent task {idx}" in goal
        assert tid in _WORKFLOWS
        assert _WORKFLOWS[tid]["goal"] == f"Concurrent task {idx} execution goal"
