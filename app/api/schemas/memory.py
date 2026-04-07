from pydantic import BaseModel, Field


class SessionCreateRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    title: str = Field(default="New Chat", description="Initial session title")


class SessionTitleRequest(BaseModel):
    session_id: str = Field(..., description="Session ID")
    prompt: str = Field(..., description="First user prompt")
