"""
REST API Routes for Agentic Workflows & Human-in-the-Loop Orchestration.
Supports multi-step task planning, status tracking, approval gates, verification,
and developer test execution.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.security.guard import verify_api_token
from app.tools.workflow_tools import (
    _WORKFLOWS,
    create_task_plan,
    get_task_status,
    request_task_approval,
    approve_task_step,
    verify_task_result,
    run_project_tests,
    summarize_test_failures,
)

router = APIRouter(prefix="/workflows", tags=["Workflows & Orchestration"])


class CreatePlanRequest(BaseModel):
    goal: str = Field(..., description="High-level business or engineering goal")
    proposed_steps: Optional[str] = Field(
        "", description="Optional newline-separated step list"
    )


class ApprovalRequest(BaseModel):
    action_description: str = Field(..., description="Action description needing human review")


class ApprovalDecisionRequest(BaseModel):
    approved: bool = Field(True, description="True to grant approval, False to reject")


class VerifyRequest(BaseModel):
    verification_criteria: str = Field(..., description="Criteria to validate against")


class TestRunRequest(BaseModel):
    test_target: Optional[str] = Field("tests/", description="Target test directory or file")


class DiagnoseRequest(BaseModel):
    test_output: str = Field(..., description="Pytest raw stdout/stderr output")


@router.post("/plan", dependencies=[Depends(verify_api_token)])
def create_plan(req: CreatePlanRequest):
    """Decompose a goal into verifiable steps with approval gates."""
    result = create_task_plan(goal=req.goal, proposed_steps=req.proposed_steps)
    # Extract newly created task ID from _WORKFLOWS
    latest_id = list(_WORKFLOWS.keys())[-1] if _WORKFLOWS else None
    return {
        "task_id": latest_id,
        "plan": result,
        "workflow": _WORKFLOWS.get(latest_id),
    }


@router.get("/tasks")
def list_tasks():
    """List all tracked workflows and their current status."""
    summaries = []
    for tid, wf in _WORKFLOWS.items():
        summaries.append({
            "task_id": tid,
            "goal": wf["goal"],
            "status": wf["status"],
            "created_at": wf["created_at"],
            "total_steps": len(wf.get("steps", [])),
        })
    return {"total": len(summaries), "tasks": summaries}


@router.get("/tasks/{task_id}")
def get_task(task_id: str):
    """Get live details, steps, and audit logs of a workflow."""
    wf = _WORKFLOWS.get(task_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{task_id}' not found.")
    status_text = get_task_status(task_id)
    return {
        "task_id": task_id,
        "status_summary": status_text,
        "details": wf,
    }


@router.post("/tasks/{task_id}/approval-request", dependencies=[Depends(verify_api_token)])
def request_approval(task_id: str, req: ApprovalRequest):
    """Pause a workflow step and request human authorization."""
    if task_id not in _WORKFLOWS:
        raise HTTPException(status_code=404, detail=f"Workflow '{task_id}' not found.")
    msg = request_task_approval(task_id, req.action_description)
    return {"task_id": task_id, "message": msg, "workflow": _WORKFLOWS[task_id]}


@router.post("/tasks/{task_id}/approve", dependencies=[Depends(verify_api_token)])
def submit_approval(task_id: str, req: ApprovalDecisionRequest):
    """Record human approval or rejection for a pending action."""
    if task_id not in _WORKFLOWS:
        raise HTTPException(status_code=404, detail=f"Workflow '{task_id}' not found.")
    msg = approve_task_step(task_id, req.approved)
    return {"task_id": task_id, "approved": req.approved, "message": msg, "workflow": _WORKFLOWS[task_id]}


@router.post("/tasks/{task_id}/verify", dependencies=[Depends(verify_api_token)])
def verify_workflow(task_id: str, req: VerifyRequest):
    """Verify workflow outputs against criteria and produce an evidence audit."""
    if task_id not in _WORKFLOWS:
        raise HTTPException(status_code=404, detail=f"Workflow '{task_id}' not found.")
    msg = verify_task_result(task_id, req.verification_criteria)
    return {"task_id": task_id, "message": msg, "workflow": _WORKFLOWS[task_id]}


@router.post("/run-tests", dependencies=[Depends(verify_api_token)])
def trigger_tests(req: TestRunRequest):
    """Safely execute pytest suite in restricted subprocess."""
    result = run_project_tests(test_target=req.test_target or "tests/")
    return {"result": result}


@router.post("/diagnose-failures")
def diagnose_output(req: DiagnoseRequest):
    """Diagnose raw test runner failure outputs."""
    summary = summarize_test_failures(req.test_output)
    return {"diagnosis": summary}
