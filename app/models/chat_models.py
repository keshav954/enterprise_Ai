import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.config.settings import settings

SESSION_ID_PATTERN = r"^[A-Za-z0-9_-]{8,64}$"
SESSION_ID_REGEX = re.compile(SESSION_ID_PATTERN)


class ChatRequest(BaseModel):
    message: str = Field(..., description="User message text (1 to MAX_MESSAGE_CHARS characters)")
    session_id: Optional[str] = Field(
        None,
        description="Optional session ID matching ^[A-Za-z0-9_-]{8,64}$",
    )

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("Message must be between 1 and 4000 characters and cannot be empty.")
        max_chars = settings.max_message_chars
        if len(v) > max_chars:
            raise ValueError(f"Message exceeds maximum allowed length of {max_chars} characters.")
        return v

    @field_validator("session_id")
    @classmethod
    def validate_session_id(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not SESSION_ID_REGEX.match(v):
                raise ValueError("session_id must match ^[A-Za-z0-9_-]{8,64}$")
        return v
