"""Document repository — data access for documents and chunks."""

from __future__ import annotations

from typing import Any, Sequence

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.document import Document, DocumentChunk
from app.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    """Repository for document and chunk data access."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, Document)

    async def get_published(
        self,
        limit: int = 50,
        offset: int = 0,
        tags: list[str] | None = None,
        status: str = "approved",
    ) -> Sequence[Document]:
        """Fetch published documents with optional tag filtering."""
        stmt = select(Document).where(Document.status == status)
        if tags:
            for tag in tags:
                stmt = stmt.where(Document.tags.contains([tag]))
        stmt = (
            stmt.order_by(Document.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_by_canonical_url(self, url: str) -> Document | None:
        """Fetch a document by its canonical URL (unique constraint)."""
        stmt = select(Document).where(Document.canonical_url == url)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_source_domain(
        self,
        domain: str,
        limit: int = 20,
    ) -> Sequence[Document]:
        """Fetch documents from a specific source domain."""
        stmt = (
            select(Document)
            .where(Document.source_domain == domain)
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def search_by_title(
        self,
        query: str,
        limit: int = 20,
    ) -> Sequence[Document]:
        """Full-text search on document titles (case-insensitive)."""
        stmt = (
            select(Document)
            .where(Document.title.ilike(f"%{query}%"))
            .order_by(Document.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_with_chunks(self, doc_id: str) -> Document | None:
        """Fetch a document with its chunks eagerly loaded."""
        stmt = (
            select(Document)
            .options(selectinload(Document.chunks))
            .where(Document.id == doc_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_chunks_by_document(
        self,
        document_id: str,
        limit: int = 100,
    ) -> Sequence[DocumentChunk]:
        """Fetch all chunks belonging to a document."""
        stmt = (
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def bulk_create_chunks(self, chunks: list[DocumentChunk]) -> int:
        """Insert multiple chunks in a single flush."""
        self.db.add_all(chunks)
        await self.db.flush()
        return len(chunks)

    async def count_by_status(self, status: str) -> int:
        """Count documents with a specific status."""
        stmt = select(func.count()).select_from(Document).where(Document.status == status)
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def get_stats(self) -> dict[str, int]:
        """Return document statistics."""
        stmt = select(
            Document.status,
            func.count(Document.id),
        ).group_by(Document.status)
        result = await self.db.execute(stmt)
        rows = result.all()
        stats = dict(rows)
        return {
            "total": sum(stats.values()),
            "approved": stats.get("approved", 0),
            "pending": stats.get("pending", 0),
            "rejected": stats.get("rejected", 0),
        }


class ChunkRepository(BaseRepository[DocumentChunk]):
    """Repository for document chunk data access."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, DocumentChunk)

    async def get_by_vector_id(self, vector_id: str) -> DocumentChunk | None:
        """Fetch a chunk by its Qdrant vector ID."""
        stmt = select(DocumentChunk).where(DocumentChunk.vector_id == vector_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_chunks_by_token_range(
        self,
        document_id: str,
        min_tokens: int,
        max_tokens: int,
    ) -> Sequence[DocumentChunk]:
        """Fetch chunks whose token count falls within a range."""
        stmt = (
            select(DocumentChunk)
            .where(
                and_(
                    DocumentChunk.document_id == document_id,
                    DocumentChunk.token_count >= min_tokens,
                    DocumentChunk.token_count <= max_tokens,
                )
            )
            .order_by(DocumentChunk.chunk_index)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()
