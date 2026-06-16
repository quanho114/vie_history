"""Feedback routes."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user, CurrentUser
from app.models.feedback import Feedback
from app.models.session import Session, Message
from app.schemas.feedback import FeedbackCreate, FeedbackResponse


router = APIRouter()


@router.post("", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def create_feedback(
    data: FeedbackCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Create feedback for a message."""
    # Verify message exists
    result = await db.execute(
        select(Message).where(Message.id == data.message_id)
    )
    message = result.scalar_one_or_none()

    if message is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found",
        )

    # Check if feedback already exists
    existing = await db.execute(
        select(Feedback).where(Feedback.message_id == data.message_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Feedback already exists for this message",
        )

    # Create feedback
    feedback = Feedback(
        message_id=data.message_id,
        score=data.score,
        comment=data.comment,
    )
    db.add(feedback)
    await db.commit()
    await db.refresh(feedback)

    return FeedbackResponse.model_validate(feedback)


@router.get("/message/{message_id}")
async def get_feedback_for_message(
    message_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Get feedback for a message."""
    result = await db.execute(
        select(Feedback).where(Feedback.message_id == message_id)
    )
    feedback = result.scalar_one_or_none()

    if feedback is None:
        return None

    return FeedbackResponse.model_validate(feedback)
