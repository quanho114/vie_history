"""Document and DocumentChunk models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    String,
    Text,
    DateTime,
    Float,
    Integer,
    ForeignKey,
    Index,
    func,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Document(Base):
    """Ingested document model."""

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint("canonical_url", name="uq_documents_canonical_url"),
        Index("idx_documents_status", "status"),
        Index("idx_documents_created_at", "created_at"),
        Index("idx_documents_status_created", "status", "created_at"),
        Index("idx_documents_author", "author"),
        Index("idx_documents_source_domain", "source_domain"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    canonical_url: Mapped[str | None] = mapped_column(
        Text,
        unique=True,
        nullable=True,
        index=True,
    )
    source_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_type: Mapped[str] = mapped_column(
        String(50),
        default="unknown",
    )
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    language: Mapped[str] = mapped_column(String(10), default="vi")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    detected_years: Mapped[list[int] | None] = mapped_column(
        ARRAY(Integer),
        nullable=True,
    )
    entity_persons: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )
    entity_places: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )
    entity_organizations: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )
    entity_events: Mapped[list[str] | None] = mapped_column(
        ARRAY(String),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
    )
    quality_score: Mapped[float] = mapped_column(Float, default=0.0)
    period: Mapped[str | None] = mapped_column(String(50), nullable=True)  # e.g. "1945-1954", "1954-1975"
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)  # primary year
    event_type: Mapped[str | None] = mapped_column(String(50), nullable=True)  # diplomatic, military, political, cultural
    confidence: Mapped[float] = mapped_column(Float, default=0.0)  # extraction confidence 0-1
    historical_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)  # flexible historical metadata
    dynasty: Mapped[str | None] = mapped_column(String(100), nullable=True)
    geographical_region: Mapped[str | None] = mapped_column(String(100), nullable=True)
    raw_content_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    markdown_content_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
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

    # Relationships
    creator: Mapped["User | None"] = relationship("User", back_populates="documents")
    project: Mapped["Project | None"] = relationship("Project", foreign_keys=[project_id])
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )
    ingest_jobs: Mapped[list["IngestJob"]] = relationship(
        "IngestJob",
        back_populates="document",
    )

    def __repr__(self) -> str:
        return f"<Document {self.title[:50]}>"


class DocumentChunk(Base):
    """Document chunk model for retrieval."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("idx_chunks_document_id", "document_id"),
        Index("idx_chunks_token_count", "token_count"),
    )

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
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    section_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vector_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    chunk_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks",
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk {self.id} idx={self.chunk_index}>"
