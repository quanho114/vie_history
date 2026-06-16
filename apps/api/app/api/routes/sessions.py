"""Sessions routes."""

import datetime
import os
from uuid import uuid4

from app.core.logging import get_logger
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user, CurrentUser, OptionalUser
from app.models.session import Session, Message
from app.schemas.session import (
    SessionCreate,
    SessionResponse,
    SessionListResponse,
    MessageResponse,
    MessageListResponse,
)


DEV_BYPASS = (
    os.environ.get("APP_ENV") == "development"
    and os.environ.get("DEV_AUTH_BYPASS_ENABLED", "false").lower() == "true"
)

logger = get_logger("sessions")


router = APIRouter()


def _display_title(session: Session) -> str:
    """Prefer a meaningful first user message over legacy generic titles."""
    title = (session.title or "").strip()
    if title and title.lower() not in {"session", "new conversation", "cuộc trò chuyện mới"}:
        return title

    first_user_message = next(
        (message.content.strip() for message in session.messages if message.role == "user" and message.content.strip()),
        "",
    )
    if first_user_message:
        return first_user_message[:80]
    return "Cuộc trò chuyện mới"


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 20,
):
    """List all sessions for current user."""
    try:
        offset = (page - 1) * page_size

        count_result = await db.execute(
            select(func.count(Session.id)).where(Session.user_id == current_user.id)
        )
        total = count_result.scalar() or 0

        result = await db.execute(
            select(Session)
            .where(Session.user_id == current_user.id)
            .options(selectinload(Session.messages))
            .order_by(Session.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        sessions = result.scalars().all()

        session_responses = []
        for session in sessions:
            session_responses.append(
                SessionResponse(
                    id=session.id,
                    user_id=session.user_id,
                    title=_display_title(session),
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    message_count=len(session.messages),
                )
            )

        return SessionListResponse(sessions=session_responses, total=total)
    except (DBAPIError, OSError):
        return SessionListResponse(sessions=[], total=0)


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    data: SessionCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a new session."""
    try:
        session = Session(id=str(uuid4()), user_id=current_user.id, title=data.title or "Session")
        db.add(session)
        await db.commit()
        await db.refresh(session)
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=session.title,
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=0,
        )
    except (DBAPIError, OSError):
        sid = str(uuid4())
        now = datetime.datetime.now(datetime.timezone.utc)
        return SessionResponse(
            id=sid,
            user_id=current_user.id,
            title=data.title or "Session",
            created_at=now,
            updated_at=now,
            message_count=0,
        )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Get a session by ID."""
    try:
        result = await db.execute(
            select(Session)
            .where(Session.id == session_id, Session.user_id == current_user.id)
            .options(selectinload(Session.messages))
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=_display_title(session),
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(session.messages),
        )
    except HTTPException:
        raise
    except (DBAPIError, OSError):
        now = datetime.datetime.now(datetime.timezone.utc)
        return SessionResponse(
            id=session_id,
            user_id=current_user.id,
            title=f"Session {session_id[:8]}",
            created_at=now,
            updated_at=now,
            message_count=0,
        )


@router.get("/{session_id}/messages", response_model=MessageListResponse)
async def get_session_messages(
    session_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = 1,
    page_size: int = 50,
):
    """Get messages for a session."""
    try:
        result = await db.execute(
            select(Session).where(
                Session.id == session_id, Session.user_id == current_user.id
            )
        )
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

        offset = (page - 1) * page_size
        count_result = await db.execute(
            select(func.count(Message.id)).where(Message.session_id == session_id)
        )
        total = count_result.scalar() or 0

        result = await db.execute(
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at)
            .offset(offset)
            .limit(page_size)
        )
        messages = result.scalars().all()
        return MessageListResponse(
            messages=[MessageResponse.model_validate(m) for m in messages], total=total
        )
    except HTTPException:
        raise
    except (DBAPIError, OSError):
        return MessageListResponse(messages=[], total=0)


@router.patch("/{session_id}", response_model=SessionResponse)
async def rename_session(
    session_id: str,
    data: SessionCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Rename a session."""
    try:
        result = await db.execute(
            select(Session)
            .where(Session.id == session_id, Session.user_id == current_user.id)
            .options(selectinload(Session.messages))
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        if data.title:
            session.title = data.title
        await db.commit()
        await db.refresh(session)
        return SessionResponse(
            id=session.id,
            user_id=session.user_id,
            title=_display_title(session),
            created_at=session.created_at,
            updated_at=session.updated_at,
            message_count=len(session.messages),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("rename_session_failed", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to rename session")


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: str,
    current_user: OptionalUser,
    db: AsyncSession = Depends(get_db),
):
    """Delete a session."""
    try:
        if current_user is None and settings.APP_ENV != "development":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )

        filters = [Session.id == session_id]
        if current_user is not None:
            filters.append(Session.user_id == current_user.id)

        result = await db.execute(select(Session).where(*filters))
        session = result.scalar_one_or_none()
        if session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")
        await db.delete(session)
        await db.commit()
        return {}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("delete_session_failed", session_id=session_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to delete session")
