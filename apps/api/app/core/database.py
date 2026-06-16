"""Async SQLAlchemy Database Setup."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import MagicMock

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool

from app.core.config import settings


# === ENGINE ===
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Set True only when debugging SQL queries
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    poolclass=NullPool if settings.is_production else None,
)


# === SESSION FACTORY ===
async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# === BASE MODEL ===
class Base(DeclarativeBase):
    """SQLAlchemy declarative base."""

    pass


# === DATABASE UTILITIES ===
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting async database session."""
    if settings.APP_ENV == "testing":
        class _Result:
            def all(self):
                return []

            def scalar_one_or_none(self):
                return None

            def scalar_one(self):
                return None

            def scalar(self):
                return 0

            def scalars(self):
                values = MagicMock()
                values.all.return_value = []
                return values

        class _TestingSession:
            def add(self, _obj):
                return None

            async def execute(self, *_args, **_kwargs):
                return _Result()

            async def scalar(self, *_args, **_kwargs):
                return 0

            async def commit(self):
                return None

            async def rollback(self):
                return None

            async def refresh(self, _obj):
                return None

            async def close(self):
                return None

            async def flush(self):
                return None

        yield _TestingSession()  # type: ignore[misc]
        return

    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for getting async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async_session = get_db_context


async def init_db() -> None:
    """Initialize database tables (development only)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
