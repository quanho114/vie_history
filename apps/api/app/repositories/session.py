"""Session repository — data access for chat sessions and messages."""

from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import func, select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.session import Session, Message
from app.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    """Repository for session data access."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, Session)

    async def get_by_user(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0,
    ) -> Sequence[Session]:
        """Fetch all sessions belonging to a user, newest first."""
        stmt = (
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(desc(Session.updated_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_with_messages(self, session_id: str) -> Session | None:
        """Fetch a session with its messages eagerly loaded."""
        stmt = (
            select(Session)
            .options(selectinload(Session.messages))
            .where(Session.id == session_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_recent(
        self,
        user_id: str | None = None,
        limit: int = 10,
    ) -> Sequence[Session]:
        """Fetch the most recently updated sessions."""
        stmt = select(Session).order_by(desc(Session.updated_at)).limit(limit)
        if user_id:
            stmt = stmt.where(Session.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def count_by_user(self, user_id: str) -> int:
        """Count sessions for a user."""
        stmt = select(func.count()).select_from(Session).where(Session.user_id == user_id)
        result = await self.db.execute(stmt)
        return int(result.scalar_one())


class MessageRepository(BaseRepository[Message]):
    """Repository for message data access."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, Message)

    async def get_by_session(
        self,
        session_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Message]:
        """Fetch messages in a session, chronological order."""
        stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(Message.created_at)
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_recent_messages(
        self,
        session_id: str,
        limit: int = 10,
    ) -> Sequence[Message]:
        """Fetch the N most recent messages in a session."""
        stmt = (
            select(Message)
            .where(Message.session_id == session_id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        rows.reverse()  # Return in chronological order
        return rows

    async def get_conversation_context(
        self,
        session_id: str,
        current_query: str,
        limit: int = 10,
    ) -> str:
        """Build a plain-text conversation history string for LLM context.

        Returns an empty string if no history exists.
        """
        messages = await self.get_recent_messages(session_id, limit=limit)
        if not messages:
            return ""

        # Skip the current query if it's already the last message
        if messages and messages[-1].content == current_query:
            messages = messages[:-1]

        blocks = []
        for msg in messages:
            role_label = "Người dùng" if msg.role == "user" else "Trợ lý AI"
            content_cleaned = " ".join(msg.content.split())[:1000]
            blocks.append(f"{role_label}: {content_cleaned}")

        return "\n".join(blocks)

    async def count_by_session(self, session_id: str) -> int:
        """Count messages in a session."""
        stmt = (
            select(func.count())
            .select_from(Message)
            .where(Message.session_id == session_id)
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def bulk_create_messages(self, messages: list[Message]) -> int:
        """Insert multiple messages in a single flush."""
        self.db.add_all(messages)
        await self.db.flush()
        return len(messages)
