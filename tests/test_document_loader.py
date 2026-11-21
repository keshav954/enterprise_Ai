"""
Unit tests for RAG document loader (multi-format loading and text chunking).
"""
from app.rag.document_loader import (
    build_documents,
    extract_csv_text,
    split_text,
)


def test_split_text_variations():
    # Empty and whitespace
    assert split_text("") == []
    assert split_text("   \n\t  ") == []

    # Single chunk
    text = "Short text under 600 characters."
    res = split_text(text)
    assert res == [text]

    # Multiline paragraphs exceeding MAX_CHUNK_SIZE (1200)
    paragraphs = "\n\n".join([f"Paragraph {i}: " + ("content " * 40) for i in range(10)])
    chunks = split_text(paragraphs)
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 1200


def test_extract_csv_text(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("ID,Name,Role\n1,Alice,Engineer\n2,Bob,Analyst\n", encoding="utf-8")
    text = extract_csv_text(csv_file)
    assert "Columns: ID, Name, Role" in text
    assert "Alice" in text
    assert "Bob" in text


def test_build_documents_reads_knowledge_base():
    docs = build_documents()
    assert isinstance(docs, list)
    assert len(docs) > 0
    first = docs[0]
    assert "source" in first
    assert "filename" in first
    assert "text" in first
    assert "file_type" in first
