import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi import Path as APIPath

from app.models.chat_models import ChatRequest
from app.security.guard import rate_limiter
from app.services.gemini_service import (
    clear_session,
    get_session_history,
    list_sessions,
    send_message,
)
from app.tools.company_tools import TOOLS
from app.tools.workspace_tools import set_current_key_hash

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/chat", dependencies=[Depends(rate_limiter)])
def chat(request: ChatRequest, req: Request):
    req_id = getattr(req.state, "request_id", "unknown")
    key_hash = getattr(req.state, "key_hash", "")
    set_current_key_hash(key_hash)
    try:
        return send_message(
            message=request.message,
            session_id=request.session_id,
            key_hash=key_hash,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception(f"Unhandled error in chat endpoint [request_id={req_id}]")
        raise HTTPException(
            status_code=500,
            detail=f"An internal server error occurred. Request ID: {req_id}",
        )


@router.get("/tools")
def get_tools():
    return {
        "total_tools": len(TOOLS),
        "tools": [
            {
                "name": tool.__name__,
                "description": tool.__doc__.strip() if tool.__doc__ else "",
            }
            for tool in TOOLS
        ],
    }


@router.get("/sessions")
def sessions(req: Request):
    key_hash = getattr(req.state, "key_hash", "")
    return list_sessions(key_hash=key_hash)


@router.get("/chat/{session_id}/history")
def session_history(
    req: Request,
    session_id: str = APIPath(..., pattern=r"^[A-Za-z0-9_-]{8,64}$"),
):
    key_hash = getattr(req.state, "key_hash", "")
    res = get_session_history(session_id, key_hash=key_hash)
    if res is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found.",
        )
    return res


@router.delete("/chat/{session_id}")
def delete_session(
    req: Request,
    session_id: str = APIPath(..., pattern=r"^[A-Za-z0-9_-]{8,64}$"),
):
    key_hash = getattr(req.state, "key_hash", "")
    result = clear_session(session_id, key_hash=key_hash)
    if result["status"] == "error":
        raise HTTPException(
            status_code=404,
            detail=result["message"],
        )
    return result
