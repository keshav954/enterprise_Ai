from app.rag.rag_service import (
    compare_documents,
    rebuild_knowledge_base,
    search_knowledge_base,
)
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
from app.tools.workflow_tools import (
    approve_task_step,
    create_task_plan,
    get_task_status,
    request_task_approval,
    run_project_tests,
    summarize_test_failures,
    verify_task_result,
)
from app.tools.workspace_tools import (
    append_workspace_file,
    copy_workspace_item,
    count_workspace_files,
    create_workspace_folder,
    delete_workspace_file,
    delete_workspace_folder,
    get_file_information,
    list_workspace_files,
    move_workspace_item,
    read_workspace_file,
    rename_workspace_item,
    workspace_summary,
    workspace_tree,
    write_workspace_file,
)


def get_company_info():
    """
    Returns enterprise company information.
    """
    return (
        "Enterprise AI Corp Information:\n"
        "- Company Name: Enterprise AI Corp\n"
        "- Founded: 2024\n"
        "- Key Departments: Engineering, AI Research, Product Operations\n"
    )


TOOLS = [
    # Company Info
    get_company_info,

    # Workspace File Operations
    list_workspace_files,
    read_workspace_file,
    write_workspace_file,
    append_workspace_file,
    delete_workspace_file,
    create_workspace_folder,
    delete_workspace_folder,
    rename_workspace_item,
    move_workspace_item,
    copy_workspace_item,
    workspace_tree,
    workspace_summary,
    get_file_information,
    count_workspace_files,

    # Search & Inspection
    search_workspace_files,
    search_text_in_workspace,
    search_workspace_text,
    find_workspace_files,

    # Code Tools
    read_multiple_workspace_files,
    read_workspace_lines,
    replace_text_in_file,
    list_python_files,

    # RAG & Grounded Document Intelligence
    search_knowledge_base,
    rebuild_knowledge_base,
    compare_documents,

    # AI Data Analyst Suite (CSV / Excel / Visual Charts)
    analyze_csv_file,
    analyze_excel_file,
    calculate_data_summary,
    create_data_chart,
    generate_analysis_report,

    # AI Workflows (Plan -> Execute -> Verify) & Developer Suite
    create_task_plan,
    get_task_status,
    request_task_approval,
    approve_task_step,
    verify_task_result,
    run_project_tests,
    summarize_test_failures,
]
