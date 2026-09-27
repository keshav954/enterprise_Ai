"""
RAG service for Enterprise AI Employee.

Uses:
- Document loader for knowledge-base documents
- ChromaDB vector store
- SentenceTransformer embeddings
"""

from app.rag.document_loader import (
    build_documents,
    KNOWLEDGE_BASE_DIR,
)

from app.rag.vector_store import (
    search_vector_store,
    build_vector_index,
)


TOP_K = 5


def search_knowledge_base(query: str):
    """
    Search the company knowledge base using semantic vector search.
    """
def rebuild_knowledge_base():
    """
    Rebuild the knowledge-base vector index from scratch.
    Call this after adding, editing, or removing files in knowledge_base/.
    """
    result = build_vector_index()

    if result.get("status") == "error":
        return f"Rebuild failed: {result.get('message')}"

    return (
        "Knowledge base rebuilt successfully. "
        f"{result['documents']} document(s), "
        f"{result['chunks']} chunk(s), "
        f"{result['vector_count']} vector(s) indexed."
    )

    if not query or not query.strip():
        return "Please provide a search query."

    try:
        results = search_vector_store(
            query=query,
            top_k=TOP_K,
        )

    except Exception as exc:
        return (
            "Knowledge base search failed. "
            f"Error: {exc}"
        )

    if not results:
        return (
            f"No relevant information found for: "
            f"'{query}'."
        )

    output = [
        "SEMANTIC KNOWLEDGE BASE RESULTS",
        "",
    ]

    for number, result in enumerate(
        results,
        start=1,
    ):
        output.append(
            f"[Source {number}] "
            f"{result['source']} "
            f"(distance={result['distance']})"
        )

        output.append(result["text"])

        output.append("")

    return "\n".join(output)


def knowledge_base_stats():
    """
    Return knowledge-base statistics.
    """

    documents = build_documents()

    sources = sorted(
        set(
            document["source"]
            for document in documents
        )
    )

    return {
        "knowledge_base_directory": str(
            KNOWLEDGE_BASE_DIR
        ),
        "documents": len(sources),
        "chunks": len(documents),
        "sources": sources,
    }