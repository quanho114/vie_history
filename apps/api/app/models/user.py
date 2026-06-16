"""User model."""

from datetime import datetime
from typing import ClassVar
from uuid import uuid4

from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """User model for authentication."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default="user",
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
    )
    settings: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        default=dict,
    )

    # Relationships
    sessions: Mapped[list["Session"]] = relationship(
        "Session",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="creator",
    )

    def __repr__(self) -> str:
        return f"<User {self.email}>"


# === BYPASS USER FOR DEVELOPMENT (no PostgreSQL needed) ===
# Used when APP_ENV=development and no database is available.
# Provides a fully-functional dev user without any credentials check.

_bypass_user_instance: User | None = None

def get_bypass_user() -> User:
    """Return the bypass user for development."""
    global _bypass_user_instance
    if _bypass_user_instance is None:
        from datetime import timezone
        _bypass_user_instance = User(
            id="00000000-0000-0000-0000-000000000000",
            email="dev@local",
            username="dev_user",
            hashed_password="",
            role="admin",
            settings={},
            created_at=datetime.now(timezone.utc)
        )
    return _bypass_user_instance
