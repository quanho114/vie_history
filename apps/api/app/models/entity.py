"""Entity models for named entity tracking."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, Index, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Entity(Base):
    """Named entity model."""

    __tablename__ = "entities"
    __table_args__ = (
        UniqueConstraint("normalized_name", "entity_type", name="uq_entities_normalized_type"),
        Index("idx_entities_normalized_name", "normalized_name"),
        Index("idx_entities_type", "entity_type"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
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

    def __repr__(self) -> str:
        return f"<Entity {self.name} ({self.entity_type})>"


class DocumentEntity(Base):
    """Association table between documents and entities."""

    __tablename__ = "document_entities"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    document_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    frequency: Mapped[int] = mapped_column(default=1)

    def __repr__(self) -> str:
        return f"<DocumentEntity doc={self.document_id} entity={self.entity_id}>"
