"""HistoricalEvent model — Timeline Brain."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    inspect,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class HistoricalEvent(Base):
    """A discrete historical event extracted from documents or entered manually.

    Represents events in Vietnamese history (1945-1975) with temporal
    anchoring, causal attributes, and rich metadata for timeline queries.
    """

    __tablename__ = "historical_events"
    __table_args__ = (
        Index("idx_historical_events_start_year", "start_year"),
        Index("idx_historical_events_period", "period"),
        Index("idx_historical_events_event_type", "event_type"),
        Index("idx_historical_events_importance", "importance_level"),
    )

    # --- Primary key ---
    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )

    # --- Core identity ---
    event_name: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str | None] = mapped_column(
        String(500),
        unique=True,
        index=True,
        nullable=True,
    )
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Temporal anchors ---
    start_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    end_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # For rough year-only events where exact date is unknown
    start_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_year: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- Historical classification ---
    # Values: 'khang_chien_chong_phap', 'khang_chien_chong_my', 'thong_nhat', 'khac'
    period: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # 1 (minor) → 5 (pivotal)
    importance_level: Mapped[int] = mapped_column(Integer, default=1)
    # Values: battle, treaty, political, cultural, economic
    event_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # --- Causal / structural attributes ---
    causes: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    effects: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    people_involved: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)
    locations: Mapped[list[str] | None] = mapped_column(ARRAY(String), nullable=True)

    # --- Source linkage ---
    wiki_page_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("wiki_pages.id", ondelete="SET NULL"),
        nullable=True,
    )
    # IDs of Document records used to extract/verify this event
    source_document_ids: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )

    # --- Flexible metadata ---
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # --- Timestamps ---
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

    # --- Relationships ---
    wiki_page: Mapped["WikiPage | None"] = relationship(  # type: ignore[name-defined]
        "WikiPage",
        foreign_keys=[wiki_page_id],
    )
    knowledge_node: Mapped["KnowledgeNode | None"] = relationship(  # type: ignore[name-defined]
        "KnowledgeNode",
        back_populates="event",
        uselist=False,
    )

    def __repr__(self) -> str:
        return f"<HistoricalEvent {self.slug or self.event_name[:40]}>"

    @property
    def wiki_page_slug(self) -> str | None:
        """Return linked wiki slug when the relationship has been loaded."""
        state = inspect(self)
        if "wiki_page" in state.unloaded:
            return None
        return self.wiki_page.slug if self.wiki_page else None
