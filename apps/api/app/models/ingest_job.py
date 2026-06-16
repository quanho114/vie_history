"""IngestJob model."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import String, Text, DateTime, ForeignKey, Index, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IngestJob(Base):
    """Ingestion job tracking model."""

    __tablename__ = "ingest_jobs"
    __table_args__ = (
        Index("idx_ingest_jobs_status", "status"),
        Index("idx_ingest_jobs_document_id", "document_id"),
        Index("idx_ingest_jobs_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    source_input: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(20), default="url")
    status: Mapped[str] = mapped_column(
        String(20),
        default="queued",
    )
    stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    logs: Mapped[list] = mapped_column(JSONB, default=list)
    document_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
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
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
    )

    # Relationships
    document: Mapped["Document | None"] = relationship(
        "Document",
        back_populates="ingest_jobs",
    )

    def add_log(self, message: str, level: str = "info") -> None:
        """Add log entry to job."""
        new_log = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "message": message,
        }
        if self.logs is None:
            self.logs = [new_log]
        else:
            self.logs = [*self.logs, new_log]


    def __repr__(self) -> str:
        return f"<IngestJob {self.id} status={self.status}>"
