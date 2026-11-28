"""
REST API Routes for Knowledge Base (RAG) Management.
"""
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.rag.document_loader import KNOWLEDGE_BASE_DIR, SUPPORTED_EXTENSIONS
from app.rag.rag_service import knowledge_base_stats, rebuild_knowledge_base
from app.security.guard import verify_admin_key

router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB


@router.get("/stats")
def get_stats():
    """
    Get current knowledge base statistics (document count, chunk count, source files).
    """
    return knowledge_base_stats()


@router.get("/documents")
def list_documents():
    """
    List all documents currently stored in the knowledge base.
    """
    KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)
    docs = []
    for file_path in sorted(KNOWLEDGE_BASE_DIR.glob("*")):
        if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            stat = file_path.stat()
            docs.append({
                "filename": file_path.name,
                "size_bytes": stat.st_size,
                "last_modified": stat.st_mtime,
            })
    return {"total": len(docs), "documents": docs}


@router.post("/rebuild", dependencies=[Depends(verify_admin_key)])
def trigger_rebuild():
    """
    Rebuild the semantic vector index from all files in knowledge_base/.
    Admin-only operation.
    """
    result = rebuild_knowledge_base()
    return {"message": result, "stats": knowledge_base_stats()}


@router.post("/upload", dependencies=[Depends(verify_admin_key)])
async def upload_document(
    file: UploadFile = File(...),
    overwrite: bool = Query(False, description="Set to true to overwrite existing file"),
):
    """
    Upload a new document (.md, .txt, .pdf, .docx, .csv) to the knowledge base and trigger index rebuild.
    Admin-only operation. Returns 409 Conflict if duplicate unless overwrite=true is provided.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename must not be empty.")

    file_path = Path(file.filename)
    suffix = file_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{suffix}'. Supported types: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )

    safe_filename = file_path.name
    target_path = KNOWLEDGE_BASE_DIR / safe_filename

    if target_path.exists() and not overwrite:
        raise HTTPException(
            status_code=409,
            detail=f"Conflict: Document '{safe_filename}' already exists. Pass overwrite=true to overwrite.",
        )

    KNOWLEDGE_BASE_DIR.mkdir(parents=True, exist_ok=True)

    content = await file.read()
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum allowed size of {MAX_UPLOAD_BYTES // (1024 * 1024)}MB.",
        )

    target_path.write_bytes(content)

    # Rebuild index to include the new document
    rebuild_res = rebuild_knowledge_base()

    return {
        "status": "success",
        "message": f"Successfully uploaded '{safe_filename}'. {rebuild_res}",
        "stats": knowledge_base_stats(),
    }

