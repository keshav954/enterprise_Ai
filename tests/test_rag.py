"""
Tests for RAG pipeline (document loader, vector store queries, and stats).
"""
import pytest
from app.rag.document_loader import split_text, build_documents
from app.rag.rag_service import knowledge_base_stats, search_knowledge_base


def test_split_text_empty():
    assert split_text("") == []
    assert split_text("   ") == []


def test_split_text_short():
    sample = "Enterprise AI Corp was founded in 2024."
    chunks = split_text(sample)
    assert len(chunks) == 1
    assert chunks[0] == sample


def test_split_text_overlapping():
    text = "word " * 400  # 2000 chars
    chunks = split_text(text)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 1200


def test_build_documents_and_stats():
    docs = build_documents()
    assert isinstance(docs, list)
    assert len(docs) > 0
    first = docs[0]
    assert "source" in first
    assert "chunk_id" in first
    assert "text" in first

    stats = knowledge_base_stats()
    assert stats["documents"] >= 1
    assert stats["chunks"] >= 1
    assert any("company_handbook.md" in src for src in stats["sources"])


def test_search_knowledge_base_empty_query():
    res = search_knowledge_base("")
    assert "Please provide a search query" in res

