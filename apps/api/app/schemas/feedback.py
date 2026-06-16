"""Feedback schemas."""

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    """Schema for creating feedback."""

    message_id: str
    score: int | None = Field(default=None, ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class FeedbackResponse(BaseModel):
    """Schema for feedback response."""

    id: str
    message_id: str
    score: int | None = None
    comment: str | None = None

    model_config = {"from_attributes": True}
