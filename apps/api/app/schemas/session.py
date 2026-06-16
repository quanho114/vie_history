"""Session schemas."""

from datetime import datetime

from pydantic import BaseModel


class SessionCreate(BaseModel):
    """Schema for creating a session."""

    title: str | None = None


class SessionResponse(BaseModel):
    """Schema for session response."""

    id: str
    user_id: str | None = None
    title: str | None = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class SessionListResponse(BaseModel):
    """Schema for session list."""

    sessions: list[SessionResponse]
    total: int


class MessageResponse(BaseModel):
    """Schema for message response."""

    id: str
    session_id: str
    role: str
    content: str
    mode: str | None = None
    citations: list | None = None
    trace: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    """Schema for message list."""

    messages: list[MessageResponse]
    total: int
