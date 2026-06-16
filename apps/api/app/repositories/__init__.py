"""Data access layer — repository pattern.

This package provides a clean separation between business logic (services)
and data access (SQLAlchemy models). All database operations flow through
repositories, enabling testability via mocking.

Usage:
    from app.repositories import DocumentRepository, SessionRepository

    async def get_documents(db: AsyncSession, limit: int = 50):
        repo = DocumentRepository(db)
        return await repo.get_published(limit=limit)
"""

from app.repositories.base import BaseRepository
from app.repositories.document import DocumentRepository
from app.repositories.session import SessionRepository
from app.repositories.user import UserRepository
from app.repositories.knowledge_draft import KnowledgeDraftRepository

__all__ = [
    "BaseRepository",
    "DocumentRepository",
    "SessionRepository",
    "UserRepository",
    "KnowledgeDraftRepository",
]
