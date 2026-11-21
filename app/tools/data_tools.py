"""
AI Data Analyst Tool Suite for Enterprise AI Employee.
Provides deterministic data calculations, profiling, and chart generation
for CSV and Excel datasets using Pandas, NumPy, and Plotly.
"""
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import plotly.express as px

from app.tools.workspace_tools import SENSITIVE_FILES, WORKSPACE_DIR

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
CHARTS_DIR = REPORTS_DIR / "charts"


def _resolve_data_path(filename: str) -> Optional[Path]:
    """Find file in workspace or knowledge_base securely, rejecting traversal and symlink escapes."""
    clean_str = str(filename).strip()
    if (
        clean_str.startswith("/")
        or clean_str.startswith("\\")
        or Path(clean_str).is_absolute()
        or (len(clean_str) > 1 and clean_str[1] == ":")
    ):
        return None

    resolved_workspace = WORKSPACE_DIR.resolve()
    target = (WORKSPACE_DIR / clean_str).resolve()
    if (
        target.is_relative_to(resolved_workspace)
        and target.exists()
        and target.is_file()
        and target.name not in SENSITIVE_FILES
    ):
        return target

    # Check knowledge_base as fallback
    kb_dir = (PROJECT_ROOT / "knowledge_base").resolve()
    kb_target = (kb_dir / clean_str).resolve()
    if kb_target.is_relative_to(kb_dir) and kb_target.exists() and kb_target.is_file():
        return kb_target

    return None


def analyze_csv_file(filename: str) -> str:
    """
    Profile and analyze a CSV dataset: row/col count, column data types, missing values,
    and descriptive statistics for numeric columns.
    """
    file_path = _resolve_data_path(filename)
    if not file_path:
        return f"File '{filename}' not found in workspace or knowledge base."

    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        return f"Error reading CSV file '{filename}': {e}"

    rows, cols = df.shape
    missing_total = int(df.isnull().sum().sum())

    output = [
        f"### Dataset Analysis: `{filename}`",
        f"- **Rows:** {rows:,} | **Columns:** {cols} | **Total Missing Values:** {missing_total}",
        "",
        "#### Column Schema & Health",
        "| Column | Type | Non-Null Count | Missing % | Unique |",
        "|---|---|---|---|---|",
    ]

    for col in df.columns:
        dtype = str(df[col].dtype)
        non_null = int(df[col].count())
        pct_missing = round((df[col].isnull().sum() / rows) * 100, 1)
        unique_vals = int(df[col].nunique())
        output.append(f"| `{col}` | {dtype} | {non_null:,} | {pct_missing}% | {unique_vals:,} |")

    # Numeric summary
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    if numeric_cols:
        output.append("\n#### Numeric Statistical Summary (Deterministic)")
        output.append("| Column | Total Sum | Mean | Median | Min | Max | Std Dev |")
        output.append("|---|---|---|---|---|---|---|")
        for col in numeric_cols:
            c = df[col].dropna()
            if len(c) > 0:
                col_sum = f"{c.sum():,.2f}"
                col_mean = f"{c.mean():,.2f}"
                col_median = f"{c.median():,.2f}"
                col_min = f"{c.min():,.2f}"
                col_max = f"{c.max():,.2f}"
                col_std = f"{c.std():,.2f}"
                output.append(
                    f"| `{col}` | {col_sum} | {col_mean} | {col_median} | {col_min} | {col_max} | {col_std} |"
                )

    return "\n".join(output)


def analyze_excel_file(filename: str, sheet_name: str = "") -> str:
    """
    Inspect an Excel spreadsheet (.xlsx, .xls), list available sheets, and profile columns.
    """
    file_path = _resolve_data_path(filename)
    if not file_path:
        return f"Excel file '{filename}' not found."

    try:
        excel = pd.ExcelFile(file_path)
        sheets = excel.sheet_names
        chosen_sheet = sheet_name if (sheet_name and sheet_name in sheets) else sheets[0]
        df = pd.read_excel(file_path, sheet_name=chosen_sheet)
    except Exception as e:
        return f"Error reading Excel file: {e}"

    rows, cols = df.shape
    return (
        f"### Excel Workbook: `{filename}`\n"
        f"- **Available Sheets:** {', '.join(sheets)}\n"
        f"- **Inspected Sheet:** `{chosen_sheet}` ({rows:,} rows × {cols} columns)\n\n"
        f"{analyze_csv_file(filename)}"
    )


def calculate_data_summary(filename: str, group_by_column: str, metric_column: str, agg_func: str = "sum") -> str:
    """
    Perform deterministic aggregation on dataset columns:
    e.g. Total sales by product, average score by department, count by category.
    agg_func options: 'sum', 'mean', 'count', 'min', 'max'.
    """
    file_path = _resolve_data_path(filename)
    if not file_path:
        return f"File '{filename}' not found."

    try:
        df = pd.read_csv(file_path) if file_path.suffix.lower() == ".csv" else pd.read_excel(file_path)
    except Exception as e:
        return f"Error loading dataset: {e}"

    if group_by_column not in df.columns:
        return f"Column '{group_by_column}' not found. Available: {', '.join(df.columns)}"
    if metric_column not in df.columns:
        return f"Metric column '{metric_column}' not found. Available: {', '.join(df.columns)}"

    agg_func = agg_func.lower().strip()
    valid_funcs = {"sum", "mean", "count", "min", "max", "std"}
    if agg_func not in valid_funcs:
        return f"Invalid aggregation function '{agg_func}'. Allowed: {', '.join(valid_funcs)}"

    try:
        grouped = df.groupby(group_by_column)[metric_column].agg(agg_func).reset_index()
        grouped = grouped.sort_values(by=metric_column, ascending=False)
    except Exception as e:
        return f"Aggregation failed: {e}"

    output = [
        f"### Deterministic Aggregation: `{agg_func.upper()}({metric_column})` by `{group_by_column}`",
        f"Total Groups: {len(grouped):,}",
        "",
        f"| {group_by_column} | {metric_column} ({agg_func}) |",
        "|---|---|",
    ]

    for _, row in grouped.head(20).iterrows():
        val = row[metric_column]
        formatted_val = f"{val:,.2f}" if isinstance(val, (int, float, np.number)) else str(val)
        output.append(f"| {row[group_by_column]} | {formatted_val} |")

    if len(grouped) > 20:
        output.append(f"\n*(Showing top 20 of {len(grouped)} total groups)*")

    return "\n".join(output)


def create_data_chart(filename: str, x_column: str, y_column: str, chart_type: str = "bar", title: str = "") -> str:
    """
    Generate an interactive Plotly visualization for a dataset.
    chart_type options: 'bar', 'line', 'scatter', 'pie', 'box'.
    Saves HTML chart in reports/charts/ and returns file reference.
    """
    file_path = _resolve_data_path(filename)
    if not file_path:
        return f"File '{filename}' not found."

    try:
        df = pd.read_csv(file_path) if file_path.suffix.lower() == ".csv" else pd.read_excel(file_path)
    except Exception as e:
        return f"Error loading file for chart: {e}"

    if x_column not in df.columns or y_column not in df.columns:
        return f"Columns '{x_column}' or '{y_column}' not found in dataset."

    chart_type = chart_type.lower().strip()
    chart_title = title or f"{y_column} by {x_column}"

    CHARTS_DIR.mkdir(parents=True, exist_ok=True)
    out_filename = f"chart_{Path(filename).stem}_{chart_type}_{x_column}_{y_column}.html"
    out_path = CHARTS_DIR / out_filename

    try:
        if chart_type == "bar":
            fig = px.bar(df, x=x_column, y=y_column, title=chart_title, template="plotly_dark")
        elif chart_type == "line":
            fig = px.line(df, x=x_column, y=y_column, title=chart_title, template="plotly_dark")
        elif chart_type == "scatter":
            fig = px.scatter(df, x=x_column, y=y_column, title=chart_title, template="plotly_dark")
        elif chart_type == "pie":
            fig = px.pie(df, names=x_column, values=y_column, title=chart_title, template="plotly_dark")
        elif chart_type == "box":
            fig = px.box(df, x=x_column, y=y_column, title=chart_title, template="plotly_dark")
        else:
            fig = px.bar(df, x=x_column, y=y_column, title=chart_title, template="plotly_dark")

        fig.write_html(str(out_path))
    except Exception as e:
        return f"Failed to generate chart: {e}"

    rel_path = f"reports/charts/{out_filename}"
    return (
        f"✓ Successfully generated interactive `{chart_type}` chart: **{chart_title}**\n"
        f"- Chart File: `{rel_path}`\n"
        f"- Plotted {len(df):,} data points."
    )


def generate_analysis_report(filename: str, title: str, findings: str) -> str:
    """
    Generate and save a formal analysis report in reports/ with confirmed figures and evidence.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_title = title.replace(" ", "_").lower()
    report_filename = f"report_{safe_title}.md"
    report_path = REPORTS_DIR / report_filename

    report_content = [
        f"# {title}",
        f"**Target Dataset:** `{filename}`  ",
        "**Generated By:** Enterprise AI Employee (Data Intelligence Engine)  ",
        "---",
        "",
        "## Executive Summary & Findings",
        findings,
        "",
        "## Verification Notice",
        "All calculations were computed deterministically via Pandas/NumPy. Predictions and extrapolations are clearly distinguished from recorded figures.",
    ]

    report_path.write_text("\n".join(report_content), encoding="utf-8")
    return f"Report successfully generated and saved to: `reports/{report_filename}`."

