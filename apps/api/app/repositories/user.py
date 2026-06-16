"""User repository — data access for user accounts."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository for user data access."""

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(db, User)

    async def get_by_email(self, email: str) -> User | None:
        """Fetch a user by email address."""
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Fetch a user by username."""
        stmt = select(User).where(User.username == username)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_or_username(self, identifier: str) -> User | None:
        """Fetch a user by email or username."""
        stmt = select(User).where(
            (User.email == identifier) | (User.username == identifier)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_users(self, limit: int = 100) -> Sequence[User]:
        """Fetch all active (non-deleted) users."""
        stmt = (
            select(User)
            .where(User.deleted_at.is_(None))
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def email_exists(self, email: str) -> bool:
        """Check whether an email is already registered."""
        stmt = select(User.id).where(User.email == email).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def username_exists(self, username: str) -> bool:
        """Check whether a username is already taken."""
        stmt = select(User.id).where(User.username == username).limit(1)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
