"""PostgreSQL fallback retriever for grounded answers."""

from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentChunk


class SQLRetriever:
    """Simple full-text-like fallback over stored chunks and document titles."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def search(
        self,
        query: str,
        top_k: int = 8,
        filters: dict | None = None,
    ) -> list[dict[str, Any]]:
        terms = [term for term in query.split() if len(term) >= 2][:8]
        if not terms:
            terms = [query]

        conditions = []
        for term in terms:
            like = f"%{term}%"
            conditions.append(DocumentChunk.content.ilike(like))
            conditions.append(Document.title.ilike(like))

        statement = (
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(or_(*conditions))
            .order_by(Document.quality_score.desc(), DocumentChunk.chunk_index.asc())
            .limit(top_k)
        )

        if filters:
            year_range = filters.get("year_range") or [None, None]
            year_from = filters.get("year_from") or year_range[0]
            year_to = filters.get("year_to") or year_range[-1]
            if year_from and year_to:
                statement = statement.where(Document.detected_years.overlap([*range(year_from, year_to + 1)]))

        rows = (await self.db.execute(statement)).all()
        return [
            {
                "chunk_id": chunk.id,
                "document_id": document.id,
                "document_title": document.title,
                "source_url": document.source_url,
                "section_title": chunk.section_title,
                "content": chunk.content,
                "score": float(document.quality_score or 0.5),
                "vector_score": 0.0,
                "bm25_score": 0.0,
            }
            for chunk, document in rows
        ]
