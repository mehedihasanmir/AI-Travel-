from pydantic import BaseModel, Field

from app.core.config import DEFAULT_SESSION_ID


class ChatRequest(BaseModel):
    prompt: str = Field(..., description="User message")
    session_id: str = Field(
        default=DEFAULT_SESSION_ID,
        description="Session ID for conversation continuity",
    )
