from typing import Optional

from app.services.gemini_service import send_message


def run_agent(
    message: str,
    session_id: Optional[str] = None,
):
    """
    Main AI Agent entry point.

    Receives a user request and sends it through
    the existing Gemini/tool-enabled service.
    """

    if not message or not message.strip():
        return {
            "status": "error",
            "message": "Message cannot be empty.",
        }

    result = send_message(
        message=message.strip(),
        session_id=session_id,
    )

    return {
        "status": "success",
        "session_id": result["session_id"],
        "reply": result["reply"],
    }
