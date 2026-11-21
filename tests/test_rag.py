"""
Tests for RAG pipeline (document loader, vector store queries, and stats).
Fast unit tests use a mocked embedding model. Real model tests are marked @pytest.mark.slow.
"""
from typing import List

import numpy as np
import pytest

import app.rag.vector_store as vector_store
from app.rag.document_loader import build_documents, split_text
from app.rag.rag_service import compare_documents, knowledge_base_stats, search_knowledge_base


class MockEmbeddingModel:
    """Fast deterministic embedding double for CI."""
    def encode(self, texts: List[str], show_progress_bar: bool = False):
        count = len(texts)
        # Return dummy 384-dimensional normalized vectors
        vecs = np.full((count, 384), 0.05, dtype=np.float32)
        return vecs


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


def test_compare_documents():
    res = compare_documents("company_handbook.md", "product_restocking_guide.md")
    assert "Document Comparison" in res
    assert "company_handbook.md" in res
    assert "product_restocking_guide.md" in res


def test_vector_store_with_mock_embedding(monkeypatch, tmp_path):
    """
    RAG indexing and semantic search executes in milliseconds using mock embedding model.
    """
    mock_model = MockEmbeddingModel()
    monkeypatch.setattr(vector_store, "get_embedding_model", lambda: mock_model)

    # Use temporary chroma directory
    test_chroma = tmp_path / "chroma"
    monkeypatch.setattr(vector_store, "CHROMA_DIR", test_chroma)

    build_res = vector_store.build_vector_index()
    assert build_res["status"] == "success"
    assert build_res["chunks"] > 0
    assert build_res["vector_count"] > 0

    results = vector_store.search_vector_store("company vacation leave policy", top_k=2)
    assert isinstance(results, list)
    assert len(results) > 0
    assert "source" in results[0]
    assert "text" in results[0]


@pytest.mark.slow
def test_real_embedding_model_search():
    """
    Integration test using the real SentenceTransformer model (marked slow).
    """
    model = vector_store.get_embedding_model()
    embeddings = model.encode(["test text"], show_progress_bar=False)
    assert len(embeddings) == 1
    assert len(embeddings[0]) == 384
