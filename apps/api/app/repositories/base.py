"""Generic base repository — single source of all DB access."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.core.database import Base

T = TypeVar("T", bound="Base")


class BaseRepository(Generic[T]):
    """Generic CRUD repository.

    All database access for a model should flow through a subclass of this.
    This makes it possible to mock database access in tests without needing
    a real database or even an async session.
    """

    def __init__(self, db: AsyncSession, model: type[T]) -> None:
        self.db = db
        self.model = model

    async def get_by_id(self, id: Any) -> T | None:
        """Fetch a single record by primary key."""
        return await self.db.get(self.model, id)

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> list[T]:
        """Fetch all records with pagination."""
        stmt = select(self.model).limit(limit).offset(offset)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> T:
        """Create a new record and commit."""
        instance = self.model(**kwargs)
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def update(self, id: Any, **kwargs: Any) -> T | None:
        """Update an existing record by primary key."""
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def upsert(self, id: Any, **kwargs: Any) -> T:
        """Insert or update a record."""
        instance = await self.get_by_id(id)
        if instance is None:
            return await self.create(id=id, **kwargs)
        for key, value in kwargs.items():
            setattr(instance, key, value)
        await self.db.commit()
        await self.db.refresh(instance)
        return instance

    async def delete(self, id: Any) -> bool:
        """Delete a record by primary key."""
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        await self.db.delete(instance)
        await self.db.commit()
        return True

    async def count(self) -> int:
        """Return total record count."""
        stmt = select(func.count()).select_from(self.model)
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def exists(self, id: Any) -> bool:
        """Check whether a record with this ID exists."""
        instance = await self.get_by_id(id)
        return instance is not None

    async def bulk_create(self, instances: list[T]) -> int:
        """Insert multiple records in a single flush."""
        self.db.add_all(instances)
        await self.db.flush()
        return len(instances)

    async def execute_query(self, stmt: Any) -> list[T]:
        """Execute a custom SELECT statement and return results."""
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
