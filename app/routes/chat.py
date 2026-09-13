from fastapi import APIRouter, HTTPException, Path as APIPath
from app.models.chat_models import ChatRequest
from app.services.gemini_service import (
    send_message,
    list_sessions,
    clear_session,
    get_session_history,
)
from app.tools.company_tools import TOOLS

router = APIRouter()


@router.post("/chat")
def chat(request: ChatRequest):
    try:
        return send_message(
            message=request.message,
            session_id=request.session_id,
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=str(e),
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
def sessions():
    return list_sessions()


@router.get("/chat/{session_id}/history")
def session_history(session_id: str = APIPath(...)):
    return get_session_history(session_id)


@router.delete("/chat/{session_id}")
def delete_session(session_id: str = APIPath(...)):
    result = clear_session(session_id)
    if result["status"] == "error":
        raise HTTPException(
            status_code=404,
            detail=result["message"],
        )
    return result
