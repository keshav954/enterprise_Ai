from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

KNOWLEDGE_BASE_DIR = PROJECT_ROOT / "knowledge_base"

SUPPORTED_EXTENSIONS = {".txt", ".md"}

MAX_CHUNK_SIZE = 1200

CHUNK_OVERLAP = 200


def split_text(text: str):
    """Split text into overlapping chunks."""

    text = text.strip()

    if not text:
        return []

    chunks = []

    start = 0

    while start < len(text):

        end = min(
            start + MAX_CHUNK_SIZE,
            len(text),
        )

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end >= len(text):
            break

        start = end - CHUNK_OVERLAP

    return chunks


def build_documents():
    """
    Read supported knowledge-base files
    and convert them into chunks.
    """

    KNOWLEDGE_BASE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    documents = []

    for file_path in KNOWLEDGE_BASE_DIR.rglob("*"):

        if not file_path.is_file():
            continue

        if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        try:
            text = file_path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except Exception:
            continue

        chunks = split_text(text)

        for index, chunk in enumerate(chunks):

            documents.append(
                {
                    "source": str(
                        file_path.relative_to(
                            PROJECT_ROOT
                        )
                    ),
                    "chunk_id": index,
                    "text": chunk,
                }
            )

    return documents