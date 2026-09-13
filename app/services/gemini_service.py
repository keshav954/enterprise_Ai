import os
import uuid
from typing import Dict, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import chats, types

from app.tools.company_tools import TOOLS
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.config.settings import settings
from app.memory import memory_service

# Load environment variables
load_dotenv()

# Gemini Client
api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

# Model Name
MODEL_NAME = settings.gemini_model

# Maximum chat sessions
MAX_SESSIONS = settings.max_sessions

# Store chat sessions
sessions: Dict[str, chats.Chat] = {}


TOOL_MAP = {tool.__name__: tool for tool in TOOLS}
MAX_TOOL_LOOPS = 5


def execute_tool_call(call) -> str:
    """
    Executes a single tool call from Gemini and returns string output.
    """
    func_name = getattr(call, "name", None)
    if not func_name or func_name not in TOOL_MAP:
        return f"Error: Tool '{func_name}' is not registered."

    func_args = getattr(call, "args", {}) or {}
    if not isinstance(func_args, dict):
        try:
            func_args = dict(func_args)
        except Exception:
            func_args = {}

    try:
        tool_fn = TOOL_MAP[func_name]
        result = tool_fn(**func_args)
        return str(result)
    except Exception as e:
        return f"Error executing tool '{func_name}': {str(e)}"


def send_message(
    message: str,
    session_id: Optional[str] = None
):
    """
    Send a message to Gemini, handle automatic function execution loops, and maintain chat history across sessions.
    """
    if session_id is None:
        session_id = str(uuid.uuid4())

    if session_id not in sessions:
        if len(sessions) >= MAX_SESSIONS:
            oldest = next(iter(sessions))
            del sessions[oldest]

        # Load existing history from SQLite if available
        past_history = memory_service.get_history(session_id)
        chat_history = []
        if past_history:
            for item in past_history:
                role = "user" if item["role"] == "user" else "model"
                chat_history.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=item["text"])]
                    )
                )

        sessions[session_id] = client.chats.create(
            model=MODEL_NAME,
            history=chat_history if chat_history else None,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                tools=TOOLS,
            ),
        )

    # Track user message in memory
    memory_service.save_message(session_id, "user", message)

    chat = sessions[session_id]
    response = chat.send_message(message)

    tools_executed = []
    loop_count = 0

    # Automatic tool execution loop
    while getattr(response, "function_calls", None) and loop_count < MAX_TOOL_LOOPS:
        loop_count += 1
        function_responses = []

        for call in response.function_calls:
            tool_name = getattr(call, "name", "unknown")
            tool_args = getattr(call, "args", {}) or {}
            result_str = execute_tool_call(call)

            tools_executed.append({
                "tool": tool_name,
                "args": dict(tool_args) if isinstance(tool_args, dict) else str(tool_args),
                "result_snippet": result_str[:200]
            })

            function_responses.append(
                types.Part.from_function_response(
                    name=tool_name,
                    response={"result": result_str}
                )
            )

        if function_responses:
            response = chat.send_message(function_responses)
        else:
            break

    reply_text = response.text or "(No response from model)"

    # Track assistant response in memory
    memory_service.save_message(session_id, "model", reply_text)

    return {
        "session_id": session_id,
        "reply": reply_text,
        "tools_executed": tools_executed
    }



def list_sessions():
    """
    Return all active and stored sessions.
    """
    stored_sessions = memory_service.get_stored_sessions()
    active_sessions = list(sessions.keys())

    # Combine unique session IDs maintaining order
    combined = list(dict.fromkeys(active_sessions + stored_sessions))
    return {
        "total_sessions": len(combined),
        "session_ids": combined
    }


def clear_session(session_id: str):
    """
    Delete a chat session from memory and database.
    """
    in_memory = session_id in sessions
    if in_memory:
        del sessions[session_id]

    cleared = memory_service.clear_history(session_id)

    if in_memory or cleared:
        return {
            "status": "success",
            "message": "Session cleared."
        }

    return {
        "status": "error",
        "message": "Session not found."
    }



def get_session_history(session_id: str):
    """
    Retrieves recorded message history for a session.
    """
    return {
        "session_id": session_id,
        "history": memory_service.get_history(session_id)
    }