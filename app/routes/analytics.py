"""
REST API Routes for AI Data Analyst & Reporting.
Supports inspecting datasets, generating calculations, and retrieving reports/charts.
"""
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel, Field

from app.security.guard import verify_api_token
from app.tools.data_tools import (
    analyze_csv_file,
    analyze_excel_file,
    calculate_data_summary,
    REPORTS_DIR,
    CHARTS_DIR,
)
from app.tools.workspace_tools import WORKSPACE_DIR

router = APIRouter(prefix="/analytics", tags=["Analytics & Data Intelligence"])


class AnalyzeRequest(BaseModel):
    filename: str = Field(..., description="Name of the CSV or Excel file in workspace")


class CalculateRequest(BaseModel):
    filename: str = Field(..., description="CSV file name")
    group_by: str = Field(..., description="Column to group by")
    metric_column: str = Field(..., description="Numeric column to aggregate")
    operation: str = Field("sum", description="Operation: sum, mean, min, max, count")


@router.get("/datasets")
def list_datasets():
    """List all CSV and Excel datasets available in workspace."""
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    datasets = []
    for ext in ["*.csv", "*.xlsx", "*.xls"]:
        for f in WORKSPACE_DIR.glob(ext):
            stat = f.stat()
            datasets.append({
                "filename": f.name,
                "size_bytes": stat.st_size,
                "type": f.suffix.lstrip(".").upper(),
                "last_modified": stat.st_mtime,
            })
    return {"total": len(datasets), "datasets": datasets}


@router.post("/analyze", dependencies=[Depends(verify_api_token)])
def analyze_dataset(req: AnalyzeRequest):
    """Run exploratory data analysis on a specified workspace dataset."""
    suffix = Path(req.filename).suffix.lower()
    if suffix == ".csv":
        result = analyze_csv_file(req.filename)
    elif suffix in [".xlsx", ".xls"]:
        result = analyze_excel_file(req.filename)
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{suffix}'. Supported: .csv, .xlsx, .xls",
        )
    return {"filename": req.filename, "analysis": result}


@router.post("/calculate", dependencies=[Depends(verify_api_token)])
def calculate_metric(req: CalculateRequest):
    """Calculate deterministic summary statistics (Pandas aggregation) on dataset."""
    result = calculate_data_summary(
        filename=req.filename,
        group_by_column=req.group_by,
        metric_column=req.metric_column,
        agg_func=req.operation,
    )
    return {"filename": req.filename, "result": result}


@router.get("/reports")
def list_reports():
    """List all generated reports and charts."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    reports = []
    for f in sorted(REPORTS_DIR.glob("*.md")):
        reports.append({
            "name": f.name,
            "type": "markdown",
            "size_bytes": f.stat().st_size,
            "url": f"/analytics/reports/{f.name}",
        })

    charts = []
    for f in sorted(CHARTS_DIR.glob("*.html")):
        charts.append({
            "name": f.name,
            "type": "html_chart",
            "size_bytes": f.stat().st_size,
            "url": f"/analytics/charts/{f.name}",
        })

    return {
        "total_reports": len(reports),
        "total_charts": len(charts),
        "reports": reports,
        "charts": charts,
    }


@router.get("/reports/{filename}")
def get_report(filename: str):
    """View or download a generated Markdown report."""
    target = (REPORTS_DIR / filename).resolve()
    # Guard against directory traversal
    if not str(target).startswith(str(REPORTS_DIR.resolve())) or not target.exists():
        raise HTTPException(status_code=404, detail=f"Report '{filename}' not found.")
    return FileResponse(str(target), media_type="text/markdown")


@router.get("/charts/{filename}")
def get_chart(filename: str):
    """View an interactive Plotly chart."""
    target = (CHARTS_DIR / filename).resolve()
    # Guard against directory traversal
    if not str(target).startswith(str(CHARTS_DIR.resolve())) or not target.exists():
        raise HTTPException(status_code=404, detail=f"Chart '{filename}' not found.")
    return FileResponse(str(target), media_type="text/html")
