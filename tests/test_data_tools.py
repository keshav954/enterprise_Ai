"""
Unit tests for AI Data Analyst tool suite.
"""

from app.tools import data_tools
from app.tools.data_tools import (
    analyze_csv_file,
    calculate_data_summary,
    create_data_chart,
    generate_analysis_report,
)


def test_analyze_csv_file():
    res = analyze_csv_file("monthly_sales.csv")
    assert "Dataset Analysis: `monthly_sales.csv`" in res
    assert "Revenue" in res
    assert "Product_Name" in res
    assert "Numeric Statistical Summary" in res


def test_calculate_data_summary():
    # Sum of Revenue by Category
    res = calculate_data_summary("monthly_sales.csv", "Category", "Revenue", "sum")
    assert "Deterministic Aggregation" in res
    assert "Software" in res
    assert "Hardware" in res

    # Average Units_Sold by Category
    res_avg = calculate_data_summary("monthly_sales.csv", "Category", "Units_Sold", "mean")
    assert "MEAN(Units_Sold)" in res_avg


def test_calculate_data_summary_invalid_column():
    res = calculate_data_summary("monthly_sales.csv", "NonExistentCol", "Revenue", "sum")
    assert "not found" in res


def test_create_data_chart():
    res = create_data_chart(
        filename="monthly_sales.csv",
        x_column="Product_Name",
        y_column="Revenue",
        chart_type="bar",
        title="Monthly Product Revenue",
    )
    assert "Successfully generated" in res
    assert "reports/charts/" in res

    # Check chart file on disk
    charts = list(data_tools.CHARTS_DIR.glob("*.html"))
    assert len(charts) > 0


def test_generate_analysis_report():
    title = "Q4 Restocking Strategy"
    findings = "Cloud Sync Agent and Edge Gateway X1 are below their reorder thresholds."
    res = generate_analysis_report("monthly_sales.csv", title, findings)
    assert "Report successfully generated" in res

    report_file = data_tools.REPORTS_DIR / "report_q4_restocking_strategy.md"
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "Cloud Sync Agent" in content
    assert "Verification Notice" in content

