"""
Gemini Service for Enterprise AI Employee.

Architecture & Concurrency:
- Runs in a single worker process (`--workers 1 --threads 4`).
- Single-worker design is required because in-memory chat session objects (`sessions`),
  ChromaDB's PersistentClient, and SQLite cannot be safely shared across multiple
  concurrent OS processes without corruption or lock contention.
- In-memory session objects and ownership are protected across threads with `_sessions_lock`.
- Gemini client is lazy-loaded on demand (app starts fast without crashing when unconfigured).
- Supports `GEMINI_FAKE=1` test double for offline testing (strictly refused in production).
"""
import os
import threading
import uuid
from typing import Any, Dict, Optional

from dotenv import load_dotenv
from fastapi import HTTPException
from google import genai
from google.genai import types

from app.config.settings import settings
from app.memory import memory_service
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.tools.company_tools import TOOLS

# Load environment variables
load_dotenv()

# Model Name
MODEL_NAME = settings.gemini_model

# Maximum chat sessions
MAX_SESSIONS = settings.max_sessions

# Maximum characters returned by a tool to the model before truncation
MAX_TOOL_OUTPUT_CHARS = 20000

# Store chat sessions and ownership protected by a thread lock
sessions: Dict[str, Any] = {}
session_owners: Dict[str, str] = {}
_sessions_lock = threading.Lock()

TOOL_MAP = {tool.__name__: tool for tool in TOOLS}
MAX_TOOL_LOOPS = 5

_gemini_client = None
_client_lock = threading.Lock()


def is_fake_mode() -> bool:
    """Check if fake Gemini test double is enabled."""
    return settings.gemini_fake or os.getenv("GEMINI_FAKE", "").lower() in ("1", "true", "yes")


def get_gemini_client():
    """
    Returns the Gemini client lazily.
    If GEMINI_FAKE=1, returns FakeGenaiClient (refused in production).
    If no GEMINI_API_KEY is configured, returns None.
    """
    global _gemini_client

    if is_fake_mode():
        if settings.env.lower() == "production":
            raise RuntimeError("GEMINI_FAKE test double is strictly forbidden when ENV=production.")
        from app.services.fake_gemini import FakeGenaiClient
        return FakeGenaiClient()

    api_key = settings.gemini_api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None

    with _client_lock:
        if _gemini_client is None:
            _gemini_client = genai.Client(api_key=api_key)
        return _gemini_client


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
    session_id: Optional[str] = None,
    key_hash: str = "",
):
    """
    Send a message to Gemini, handle automatic function execution loops,
    and maintain caller-scoped chat history across sessions.
    """
    client = get_gemini_client()
    if client is None:
        raise HTTPException(
            status_code=503,
            detail="Gemini API is not configured. Please set GEMINI_API_KEY in the server environment.",
        )

    if session_id is None:
        session_id = str(uuid.uuid4())

    with _sessions_lock:
        # Verify session isolation: reject cross-session access
        if session_id in session_owners and key_hash and session_owners[session_id] != key_hash:
            raise HTTPException(status_code=404, detail="Session not found.")

    # Check database ownership for existing session
    past_history = memory_service.get_history(session_id, key_hash=key_hash)
    if past_history is None:
        # If session already exists in DB for a different key_hash, reject with 404
        if key_hash and memory_service.session_exists(session_id):
            raise HTTPException(status_code=404, detail="Session not found.")

    with _sessions_lock:
        if session_id not in sessions:
            if len(sessions) >= MAX_SESSIONS:
                oldest = next(iter(sessions))
                del sessions[oldest]
                if oldest in session_owners:
                    del session_owners[oldest]

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

        session_owners[session_id] = key_hash
        chat = sessions[session_id]

    # Track user message in memory
    try:
        memory_service.save_message(session_id, "user", message, key_hash=key_hash)
    except PermissionError:
        raise HTTPException(status_code=404, detail="Session not found.")

    try:
        response = chat.send_message(message)
    except Exception as e:
        error_msg = str(e)
        if "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
            friendly_err = (
                f"⚠️ **Gemini API Quota Exceeded for `{MODEL_NAME}`**\n\n"
                "Your Google Gemini API free-tier quota has been exhausted for this model.\n\n"
                "**How to resolve:**\n"
                "- Replace `GEMINI_API_KEY` in your `.env` file with a new key from [Google AI Studio](https://aistudio.google.com/).\n"
                "- Or switch to an available model in `.env` (e.g. `GEMINI_MODEL=gemini-2.5-flash-lite`).\n"
                "- Then restart the application."
            )
            return {
                "session_id": session_id,
                "reply": friendly_err,
                "tools_executed": [],
            }
        raise

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

            # Cap tool output returned to model at MAX_TOOL_OUTPUT_CHARS
            if len(result_str) > MAX_TOOL_OUTPUT_CHARS:
                result_str = (
                    result_str[:MAX_TOOL_OUTPUT_CHARS]
                    + f"\n... [Truncated: tool output exceeded {MAX_TOOL_OUTPUT_CHARS} characters]"
                )

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
            try:
                response = chat.send_message(function_responses)
            except Exception as e:
                error_msg = str(e)
                if "RESOURCE_EXHAUSTED" in error_msg or "429" in error_msg:
                    friendly_err = (
                        "⚠️ **Gemini API Quota Exceeded during tool execution**\n\n"
                        "Rate limit reached on model `" + MODEL_NAME + "`. Please update your API key in `.env`."
                    )
                    return {
                        "session_id": session_id,
                        "reply": friendly_err,
                        "tools_executed": tools_executed,
                    }
                raise
        else:
            break

    reply_text = getattr(response, "text", None) or "(No response from model)"

    # Track assistant response in memory
    memory_service.save_message(session_id, "model", reply_text, key_hash=key_hash)

    return {
        "session_id": session_id,
        "reply": reply_text,
        "tools_executed": tools_executed
    }


def list_sessions(key_hash: str = ""):
    """
    Return active and stored sessions scoped to caller's key_hash.
    """
    stored_sessions = memory_service.get_stored_sessions(key_hash=key_hash)
    with _sessions_lock:
        active_sessions = [
            sid for sid in sessions
            if not key_hash or session_owners.get(sid, "") == key_hash
        ]

    # Combine unique session IDs maintaining order
    combined = list(dict.fromkeys(active_sessions + stored_sessions))
    return {
        "total_sessions": len(combined),
        "session_ids": combined
    }


def clear_session(session_id: str, key_hash: str = ""):
    """
    Delete a chat session from memory and database, respecting caller scoping.
    """
    with _sessions_lock:
        if session_id in session_owners and key_hash and session_owners[session_id] != key_hash:
            return {
                "status": "error",
                "message": "Session not found."
            }

        in_memory = session_id in sessions
        if in_memory:
            del sessions[session_id]
        if session_id in session_owners:
            del session_owners[session_id]

    cleared = memory_service.clear_history(session_id, key_hash=key_hash)

    if in_memory or cleared:
        return {
            "status": "success",
            "message": "Session cleared."
        }

    return {
        "status": "error",
        "message": "Session not found."
    }


def get_session_history(session_id: str, key_hash: str = ""):
    """
    Retrieves recorded message history for a session scoped to caller's key_hash.
    """
    with _sessions_lock:
        if session_id in session_owners and key_hash and session_owners[session_id] != key_hash:
            return None

    history = memory_service.get_history(session_id, key_hash=key_hash)
    if history is None:
        return None

    return {
        "session_id": session_id,
        "history": history
    }
