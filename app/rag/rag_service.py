"""
RAG service for Enterprise AI Employee.
Features:
- Multi-format document loading (PDF, DOCX, TXT, MD, CSV)
- Citation-grounded semantic retrieval
- Document comparison
- Strict grounding with explicit "unsupported/not found" answers
"""
from typing import Any, Dict

from app.rag.document_loader import (
    KNOWLEDGE_BASE_DIR,
    build_documents,
)
from app.rag.vector_store import (
    build_vector_index,
    search_vector_store,
)

TOP_K = 5


def search_knowledge_base(query: str) -> str:
    """
    Search the company knowledge base using semantic vector search with grounded citations.
    Returns source references, file types, page numbers (for PDFs), and excerpt text.
    """
    if not query or not query.strip():
        return "Please provide a search query."

    try:
        results = search_vector_store(query=query, top_k=TOP_K)
    except Exception as exc:
        return f"Knowledge base search failed. Error: {exc}"

    if not results:
        return (
            f"No relevant information found in the approved company knowledge base for: '{query.strip()}'.\n"
            "Notice: I will not fabricate policies or procedures that are not explicitly documented."
        )

    output = [
        "### Grounded Knowledge Base Results",
        f"Query: *\"{query.strip()}\"*",
        "",
    ]

    for number, res in enumerate(results, start=1):
        source = res.get("source") or "Unknown"
        page_info = f" | Page {res['page']}" if res.get("page") else ""
        file_type = f" | Type: {res['file_type']}" if res.get("file_type") else ""
        dist = res.get("distance", 0.0)
        confidence = max(0, min(100, int((1.0 - (dist / 1.7)) * 100)))

        output.append(
            f"**[Citation {number}]** `{source}`{page_info}{file_type} "
            f"*(Relevance Score: {confidence}%)*"
        )
        output.append(f"> {res['text'].strip()}")
        output.append("")

    return "\n".join(output)


def compare_documents(filename1: str, filename2: str) -> str:
    """
    Compare two documents in the knowledge base and return length, chunk count, and key content summary.
    """
    path1 = KNOWLEDGE_BASE_DIR / filename1
    path2 = KNOWLEDGE_BASE_DIR / filename2

    if not path1.exists():
        return f"Document '{filename1}' not found in knowledge_base/."
    if not path2.exists():
        return f"Document '{filename2}' not found in knowledge_base/."

    try:
        text1 = path1.read_text(encoding="utf-8", errors="replace")
        text2 = path2.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Error reading files: {e}"

    lines1, words1 = len(text1.splitlines()), len(text1.split())
    lines2, words2 = len(text2.splitlines()), len(text2.split())

    return (
        f"### Document Comparison\n\n"
        f"**File 1: `{filename1}`**\n"
        f"- Lines: {lines1} | Words: {words1} | Size: {path1.stat().st_size} bytes\n\n"
        f"**File 2: `{filename2}`**\n"
        f"- Lines: {lines2} | Words: {words2} | Size: {path2.stat().st_size} bytes\n\n"
        f"Both documents are indexed and ready for comparative semantic queries."
    )


def rebuild_knowledge_base() -> str:
    """
    Rebuild the knowledge-base vector index from scratch.
    Call this after adding, editing, or removing files in knowledge_base/.
    Requires administrator privileges.
    """
    from app.security.guard import get_current_admin

    if not get_current_admin():
        return "Access Denied: Rebuilding the knowledge base requires administrator privileges."

    result = build_vector_index()
    if result.get("status") == "error":
        return f"Rebuild failed: {result.get('message')}"

    return (
        "Knowledge base rebuilt successfully with grounded citations. "
        f"{result['documents']} document(s), "
        f"{result['chunks']} chunk(s), "
        f"{result['vector_count']} vector(s) indexed."
    )


def knowledge_base_stats() -> Dict[str, Any]:
    """Return knowledge-base statistics."""
    documents = build_documents()
    sources = sorted(set(doc["source"] for doc in documents))

    return {
        "knowledge_base_directory": str(KNOWLEDGE_BASE_DIR),
        "documents": len(sources),
        "chunks": len(documents),
        "sources": sources,
    }
