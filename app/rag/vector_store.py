"""
Persistent vector store for Enterprise AI Employee.

Uses:
- ChromaDB for persistent vector storage
- SentenceTransformers for local embeddings
"""

from functools import lru_cache
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from app.rag.document_loader import build_documents

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

CHROMA_DIR = PROJECT_ROOT / "data" / "chroma"

COLLECTION_NAME = "enterprise_ai_knowledge"

EMBEDDING_MODEL = "all-MiniLM-L6-v2"

TOP_K = 5
MAX_DISTANCE = 1.7

@lru_cache(maxsize=1)
def get_embedding_model():
    """Load the embedding model once and reuse it."""
    return SentenceTransformer(EMBEDDING_MODEL)


@lru_cache(maxsize=1)
def get_chroma_client():
    """Create a persistent ChromaDB client."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    return chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )


def get_collection():
    """Get or create the knowledge-base collection."""
    client = get_chroma_client()

    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "description": "Enterprise AI Employee knowledge base"
        },
    )


def build_vector_index():
    """
    Build or rebuild the vector index
    from the knowledge-base documents.
    """

    documents = build_documents()
    if not documents:
        return {
            "status": "error",
            "message": "Knowledge base is empty.",
            "documents": 0,
            "chunks": 0,
        }

    model = get_embedding_model()

    client = get_chroma_client()

    # Remove old collection so stale chunks are not retained.
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={
            "description": "Enterprise AI Employee knowledge base"
        },
    )

    texts = [
        document["text"]
        for document in documents
    ]

    print("Creating embeddings...")

    embeddings = model.encode(
        texts,
        show_progress_bar=True,
    ).tolist()

    ids = []
    metadatas = []

    for index, document in enumerate(documents):

        ids.append(
            f"{document['source']}::{document['chunk_id']}"
        )

        metadatas.append(
            {
                "source": document["source"],
                "chunk_id": document["chunk_id"],
            }
        )

    collection.add(
        ids=ids,
        documents=texts,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    return {
        "status": "success",
        "collection": COLLECTION_NAME,
        "embedding_model": EMBEDDING_MODEL,
        "documents": len(
            set(
                document["source"]
                for document in documents
            )
        ),
        "chunks": len(documents),
        "vector_count": collection.count(),
    }


def search_vector_store(
    query: str,
    top_k: int = TOP_K,
):
    """Search the knowledge base using semantic similarity."""

    if not query or not query.strip():
        return []

    collection = get_collection()

    # Automatically build the index if it is empty.
    if collection.count() == 0:
        build_vector_index()
        collection = get_collection()

    model = get_embedding_model()

    query_embedding = model.encode(
        [query.strip()]
    ).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=top_k,
    )

    documents = results.get(
        "documents",
        [[]]
    )[0]

    metadatas = results.get(
        "metadatas",
        [[]]
    )[0]

    distances = results.get(
        "distances",
        [[]]
    )[0]

    output = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):
        if distance > MAX_DISTANCE:
            continue

        output.append(
            {
                "text": document,
                "source": metadata.get("source"),
                "chunk_id": metadata.get("chunk_id"),
                "distance": round(
                    float(distance),
                    4
                ),
            }
        )

    return output

def vector_store_stats():
    """Return vector database statistics."""

    collection = get_collection()

    return {
        "collection": COLLECTION_NAME,
        "embedding_model": EMBEDDING_MODEL,
        "database_path": str(CHROMA_DIR),
        "vector_count": collection.count(),
    }