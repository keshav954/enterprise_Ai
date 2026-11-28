"""
Universal Document Loader for Enterprise AI Employee Knowledge Base.
Supports: .md, .txt, .pdf, .docx, .csv
Extracts text with page, section, and source metadata.
"""
import csv
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "knowledge_base"

SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx", ".csv"}

MAX_CHUNK_SIZE = 1200
CHUNK_OVERLAP = 200


def split_text(
    text: str,
    chunk_size: int = MAX_CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    """Split text into overlapping chunks."""
    if not text or not text.strip():
        return []

    text = text.strip()
    chunk_size = max(50, chunk_size)
    overlap = max(0, min(overlap, chunk_size - 1))
    step = max(1, chunk_size - overlap)

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start += step

    return chunks


def extract_pdf_pages(file_path: Path) -> list[dict[str, Any]]:
    """Extract text from PDF file page by page using pypdf."""
    try:
        from pypdf import PdfReader

        sections: list[dict[str, Any]] = []
        reader = PdfReader(str(file_path))
        for page_idx, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            if page_text.strip():
                sections.append({
                    "page": page_idx,
                    "text": page_text.strip(),
                })
        return sections
    except Exception as exc:
        logger.warning("Failed to extract PDF %s: %s", file_path, exc)
        return []


def extract_docx_text(file_path: Path) -> str:
    """Extract text from Word .docx file using python-docx."""
    try:
        from docx import Document

        doc = Document(str(file_path))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except Exception as exc:
        logger.warning("Failed to extract DOCX %s: %s", file_path, exc)
        return ""


def extract_csv_text(file_path: Path) -> str:
    """Convert CSV dataset into textual representation for semantic indexing."""
    lines: list[str] = []
    try:
        with file_path.open("r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if headers:
                lines.append(f"Columns: {', '.join(headers)}")
            for row_idx, row in enumerate(reader, start=1):
                if row_idx > 100:  # Cap at first 100 rows for vector summary
                    lines.append(f"... and {row_idx} more rows in dataset.")
                    break
                if headers and len(row) == len(headers):
                    row_desc = ", ".join(f"{h}: {val}" for h, val in zip(headers, row) if val)
                    lines.append(f"Row {row_idx}: {row_desc}")
                elif any(row):
                    lines.append(f"Row {row_idx}: {', '.join(row)}")
    except Exception as e:
        return f"Error reading CSV: {e}"
    return "\n".join(lines)


def build_documents() -> list[dict[str, Any]]:
    """
    Read all supported documents in KNOWLEDGE_BASE_DIR and split them into indexed chunks.
    Preserves source file, chunk id, file type, and page number metadata.
    """
    KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    documents: list[dict[str, Any]] = []

    for file_path in sorted(KNOWLEDGE_BASE_DIR.rglob("*")):
        if not file_path.is_file():
            continue

        ext = file_path.suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            continue

        try:
            rel_source = str(file_path.relative_to(PROJECT_ROOT))
        except ValueError:
            rel_source = f"knowledge_base/{file_path.name}"

        try:
            if ext == ".pdf":
                pdf_sections = extract_pdf_pages(file_path)
                for sec in pdf_sections:
                    page_num = sec["page"]
                    chunks = split_text(sec["text"])
                    for chunk in chunks:
                        documents.append({
                            "source": rel_source,
                            "filename": file_path.name,
                            "file_type": "PDF",
                            "page": page_num,
                            "chunk_id": len(documents),
                            "text": f"[Page {page_num}] {chunk}",
                        })

            elif ext == ".docx":
                docx_text = extract_docx_text(file_path)
                chunks = split_text(docx_text)
                for chunk in chunks:
                    documents.append({
                        "source": rel_source,
                        "filename": file_path.name,
                        "file_type": "DOCX",
                        "page": None,
                        "chunk_id": len(documents),
                        "text": chunk,
                    })

            elif ext == ".csv":
                csv_text = extract_csv_text(file_path)
                chunks = split_text(csv_text)
                for chunk in chunks:
                    documents.append({
                        "source": rel_source,
                        "filename": file_path.name,
                        "file_type": "CSV",
                        "page": None,
                        "chunk_id": len(documents),
                        "text": chunk,
                    })

            else:  # .txt, .md
                raw_text = file_path.read_text(encoding="utf-8", errors="replace")
                chunks = split_text(raw_text)
                for chunk in chunks:
                    documents.append({
                        "source": rel_source,
                        "filename": file_path.name,
                        "file_type": ext.lstrip(".").upper(),
                        "page": None,
                        "chunk_id": len(documents),
                        "text": chunk,
                    })

        except Exception as err:
            logger.warning("Error parsing document %s: %s", file_path, err)
            continue

    return documents
