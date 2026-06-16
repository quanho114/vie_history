"""Knowledge evolution models — Draft Changes for Human-In-The-Loop (HITL) approval."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class KnowledgeDraft(Base):
    """A draft change proposed by the MemoryConsolidationNode.

    Change proposals undergo HITL verification through the admin panel
    before writing permanently into the Neo4j Graph Database and Wiki index.
    """

    __tablename__ = "knowledge_drafts"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    # Values: "add_node", "add_edge", "update_node", "update_edge", "contradiction"
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Values: "pending", "approved", "rejected"
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)

    # Payload detailing properties of proposed Node, Edge, or Contradiction
    draft_data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        server_default="{}",
        default=dict,
    )
    # Context of how this knowledge was extracted (e.g. query, session_id, citation source)
    source_info: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

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

    def __repr__(self) -> str:
        return f"<KnowledgeDraft [{self.change_type}] status={self.status}>"
