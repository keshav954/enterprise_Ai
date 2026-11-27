"""
Unit tests for RAG document loader (multi-format loading and text chunking).
"""
from app.rag.document_loader import (
    build_documents,
    extract_csv_text,
    extract_docx_text,
    extract_pdf_pages,
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

    # Custom chunk_size and overlap
    custom_chunks = split_text("1234567890" * 20, chunk_size=50, overlap=10)
    assert len(custom_chunks) > 1
    assert all(len(c) <= 50 for c in custom_chunks)


def test_extract_csv_text(tmp_path):
    csv_file = tmp_path / "test.csv"
    csv_file.write_text("ID,Name,Role\n1,Alice,Engineer\n2,Bob,Analyst\n", encoding="utf-8")
    text = extract_csv_text(csv_file)
    assert "Columns: ID, Name, Role" in text
    assert "Alice" in text
    assert "Bob" in text


def test_extract_csv_text_error(tmp_path):
    # Non-existent file should gracefully return error string
    non_existent = tmp_path / "missing.csv"
    text = extract_csv_text(non_existent)
    assert "Error reading CSV" in text


def test_extract_pdf_and_docx_graceful_failures(tmp_path):
    # Corrupt or non-existent PDF
    bad_pdf = tmp_path / "bad.pdf"
    bad_pdf.write_text("Not a real PDF", encoding="utf-8")
    sections = extract_pdf_pages(bad_pdf)
    assert sections == []

    # Corrupt or non-existent DOCX
    bad_docx = tmp_path / "bad.docx"
    bad_docx.write_text("Not a real docx", encoding="utf-8")
    text = extract_docx_text(bad_docx)
    assert text == ""


def test_build_documents_reads_knowledge_base():
    docs = build_documents()
    assert isinstance(docs, list)
    assert len(docs) > 0
    first = docs[0]
    assert "source" in first
    assert "filename" in first
    assert "text" in first
    assert "file_type" in first
