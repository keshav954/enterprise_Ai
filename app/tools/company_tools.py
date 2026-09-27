from app.rag.rag_service import search_knowledge_base, rebuild_knowledge_base

from app.tools.workspace_tools import (
    WORKSPACE_DIR,
    SENSITIVE_FILES,
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
)

from app.tools.search_tools import (
    search_workspace_files,
    search_text_in_workspace,
    search_workspace_text,
    find_workspace_files,
)

from app.tools.code_tools import (
    read_multiple_workspace_files,
    read_workspace_lines,
    replace_text_in_file,
    list_python_files,
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
    # Company
    get_company_info,

    # Workspace
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

    # Search
    search_workspace_files,
    search_text_in_workspace,
    search_workspace_text,
    find_workspace_files,

    # Code
    read_multiple_workspace_files,
    read_workspace_lines,
    replace_text_in_file,
    list_python_files,

     # RAG / Knowledge Base
    search_knowledge_base,
    rebuild_knowledge_base,
]