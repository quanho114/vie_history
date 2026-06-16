"""Add timeline and graph tables.

Revision ID: 003_timeline_graph
Revises: 002_brain
Create Date: 2026-05-20

Tables created:
  - historical_events  (Timeline Brain)
  - knowledge_nodes    (Graph Brain)
  - knowledge_edges    (Graph Brain)

Note: This migration depends on 002_brain which adds the wiki_pages table
referenced by historical_events.wiki_page_id and knowledge_nodes.wiki_page_id.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003_timeline_graph"
down_revision: Union[str, None] = "002_brain"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # historical_events
    # ------------------------------------------------------------------
    op.create_table(
        "historical_events",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
        ),
        sa.Column("event_name", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(500), unique=True, nullable=True),
        sa.Column("summary", sa.Text, nullable=True),
        sa.Column("start_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_year", sa.Integer, nullable=True),
        sa.Column("end_year", sa.Integer, nullable=True),
        sa.Column("period", sa.String(50), nullable=True),
        sa.Column("importance_level", sa.Integer, server_default="1", nullable=False),
        sa.Column("event_type", sa.String(50), nullable=True),
        sa.Column("causes", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("effects", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("people_involved", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column("locations", postgresql.ARRAY(sa.String), nullable=True),
        sa.Column(
            "wiki_page_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("wiki_pages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "source_document_ids", postgresql.ARRAY(sa.String), nullable=True
        ),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_historical_events_slug", "historical_events", ["slug"], unique=True
    )
    op.create_index(
        "idx_historical_events_start_year", "historical_events", ["start_year"]
    )
    op.create_index(
        "idx_historical_events_period", "historical_events", ["period"]
    )
    op.create_index(
        "idx_historical_events_event_type", "historical_events", ["event_type"]
    )
    op.create_index(
        "idx_historical_events_importance",
        "historical_events",
        ["importance_level"],
    )

    # ------------------------------------------------------------------
    # knowledge_nodes
    # ------------------------------------------------------------------
    op.create_table(
        "knowledge_nodes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
        ),
        sa.Column("node_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(500), nullable=False),
        sa.Column("slug", sa.String(500), unique=True, nullable=True),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "wiki_page_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("wiki_pages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "event_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("historical_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_knowledge_nodes_slug", "knowledge_nodes", ["slug"], unique=True
    )
    op.create_index(
        "idx_knowledge_nodes_node_type", "knowledge_nodes", ["node_type"]
    )

    # ------------------------------------------------------------------
    # knowledge_edges
    # ------------------------------------------------------------------
    op.create_table(
        "knowledge_edges",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=False),
            primary_key=True,
        ),
        sa.Column(
            "source_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "target_id",
            postgresql.UUID(as_uuid=False),
            sa.ForeignKey("knowledge_nodes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("edge_type", sa.String(50), nullable=False),
        sa.Column("weight", sa.Float, server_default="1.0", nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_knowledge_edges_source_target",
        "knowledge_edges",
        ["source_id", "target_id"],
    )
    op.create_index(
        "idx_knowledge_edges_edge_type", "knowledge_edges", ["edge_type"]
    )


def downgrade() -> None:
    # Drop in reverse dependency order
    op.drop_index("idx_knowledge_edges_edge_type", table_name="knowledge_edges")
    op.drop_index(
        "idx_knowledge_edges_source_target", table_name="knowledge_edges"
    )
    op.drop_table("knowledge_edges")

    op.drop_index("idx_knowledge_nodes_node_type", table_name="knowledge_nodes")
    op.drop_index("ix_knowledge_nodes_slug", table_name="knowledge_nodes")
    op.drop_table("knowledge_nodes")

    op.drop_index(
        "idx_historical_events_importance", table_name="historical_events"
    )
    op.drop_index(
        "idx_historical_events_event_type", table_name="historical_events"
    )
    op.drop_index(
        "idx_historical_events_period", table_name="historical_events"
    )
    op.drop_index(
        "idx_historical_events_start_year", table_name="historical_events"
    )
    op.drop_index("ix_historical_events_slug", table_name="historical_events")
    op.drop_table("historical_events")
