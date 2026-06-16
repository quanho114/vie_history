"""Knowledge graph models — Graph Brain.

Two-table graph: KnowledgeNode + KnowledgeEdge.
Nodes represent entities (people, events, places, …);
Edges represent typed relations between them.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class KnowledgeNode(Base):
    """A vertex in the Vietnamese-history knowledge graph.

    Nodes are typed entities: people, events, organisations, locations,
    concepts, agreements, battles, time periods, or source documents.
    Each node can optionally be linked to a WikiPage or HistoricalEvent
    for enriched context.
    """

    __tablename__ = "knowledge_nodes"
    __table_args__ = (
        Index("idx_knowledge_nodes_node_type", "node_type"),
        Index("idx_knowledge_nodes_slug", "slug"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    # Values: Event, Person, Organization, Location, Document,
    #         Agreement, Battle, Period, Concept
    node_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    slug: Mapped[str | None] = mapped_column(
        String(500),
        unique=True,
        index=True,
        nullable=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Optional cross-links
    wiki_page_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("wiki_pages.id", ondelete="SET NULL"),
        nullable=True,
    )
    event_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("historical_events.id", ondelete="SET NULL"),
        nullable=True,
    )

    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

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
    event: Mapped["HistoricalEvent | None"] = relationship(  # type: ignore[name-defined]
        "HistoricalEvent",
        back_populates="knowledge_node",
        foreign_keys=[event_id],
    )
    outgoing_edges: Mapped[list["KnowledgeEdge"]] = relationship(
        "KnowledgeEdge",
        foreign_keys="[KnowledgeEdge.source_id]",
        back_populates="source",
        cascade="all, delete-orphan",
    )
    incoming_edges: Mapped[list["KnowledgeEdge"]] = relationship(
        "KnowledgeEdge",
        foreign_keys="[KnowledgeEdge.target_id]",
        back_populates="target",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<KnowledgeNode [{self.node_type}] {self.slug or self.name[:40]}>"


class KnowledgeEdge(Base):
    """A directed, typed edge between two KnowledgeNodes.

    Edge types capture the semantic relation:
    - PARTICIPATED_IN, LED_BY, HAPPENED_AT
    - HAPPENED_AFTER, CAUSED_BY, LED_TO
    - MENTIONED_IN, RELATED_TO, SIGNED_BY, OPPOSED
    """

    __tablename__ = "knowledge_edges"
    __table_args__ = (
        Index("idx_knowledge_edges_source_target", "source_id", "target_id"),
        Index("idx_knowledge_edges_edge_type", "edge_type"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    source_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
        nullable=False,
    )
    # e.g. PARTICIPATED_IN, LED_BY, HAPPENED_AT, CAUSED_BY, LED_TO, etc.
    edge_type: Mapped[str] = mapped_column(String(50), nullable=False)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # --- Relationships ---
    source: Mapped["KnowledgeNode"] = relationship(
        "KnowledgeNode",
        foreign_keys=[source_id],
        back_populates="outgoing_edges",
    )
    target: Mapped["KnowledgeNode"] = relationship(
        "KnowledgeNode",
        foreign_keys=[target_id],
        back_populates="incoming_edges",
    )

    def __repr__(self) -> str:
        return f"<KnowledgeEdge {self.source_id} --[{self.edge_type}]--> {self.target_id}>"
