"""Knowledge draft repository — data access for HITL approval queue."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evolution import KnowledgeDraft
from app.repositories.base import BaseRepository


class KnowledgeDraftRepository(BaseRepository[KnowledgeDraft]):
    """Repository for knowledge draft data access."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, KnowledgeDraft)

    async def get_pending(self, limit: int = 50, offset: int = 0) -> Sequence[KnowledgeDraft]:
        """Fetch drafts awaiting review (status=pending)."""
        stmt = (
            select(KnowledgeDraft)
            .where(KnowledgeDraft.status == "pending")
            .order_by(desc(KnowledgeDraft.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_status(
        self,
        status: str,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[KnowledgeDraft]:
        """Fetch drafts by status (pending / approved / rejected)."""
        stmt = (
            select(KnowledgeDraft)
            .where(KnowledgeDraft.status == status)
            .order_by(desc(KnowledgeDraft.created_at))
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_change_type(
        self,
        change_type: str,
        limit: int = 50,
    ) -> Sequence[KnowledgeDraft]:
        """Fetch drafts by change type (add_node / add_edge / contradiction)."""
        stmt = (
            select(KnowledgeDraft)
            .where(KnowledgeDraft.change_type == change_type)
            .order_by(desc(KnowledgeDraft.created_at))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def approve(self, draft_id: str) -> KnowledgeDraft | None:
        """Mark a draft as approved."""
        return await self.update(draft_id, status="approved")

    async def reject(self, draft_id: str) -> KnowledgeDraft | None:
        """Mark a draft as rejected."""
        return await self.update(draft_id, status="rejected")

    async def count_pending(self) -> int:
        """Return the number of drafts awaiting review."""
        stmt = (
            select(KnowledgeDraft)
            .where(KnowledgeDraft.status == "pending")
        )
        result = await self.db.execute(stmt)
        return len(result.scalars().all())
