"""Pydantic schemas for the Graph Brain (knowledge nodes & edges)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Node schemas
# ---------------------------------------------------------------------------


class KnowledgeNodeCreate(BaseModel):
    """Payload for creating a knowledge graph node."""

    node_type: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=500)
    slug: str | None = Field(default=None, max_length=500)
    description: str | None = None
    wiki_page_id: str | None = None
    event_id: str | None = None
    metadata_json: dict[str, Any] | None = None


class KnowledgeNodeUpdate(BaseModel):
    """Payload for partially updating a knowledge node."""

    node_type: str | None = Field(default=None, max_length=50)
    name: str | None = Field(default=None, max_length=500)
    slug: str | None = Field(default=None, max_length=500)
    description: str | None = None
    wiki_page_id: str | None = None
    event_id: str | None = None
    metadata_json: dict[str, Any] | None = None


class KnowledgeNodeResponse(BaseModel):
    """Full knowledge node response."""

    id: str
    node_type: str
    name: str
    slug: str | None
    description: str | None
    wiki_page_id: str | None
    event_id: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeNodeListResponse(BaseModel):
    """Paginated list of knowledge nodes."""

    nodes: list[KnowledgeNodeResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Edge schemas
# ---------------------------------------------------------------------------


class KnowledgeEdgeCreate(BaseModel):
    """Payload for creating a directed graph edge."""

    source_id: str
    target_id: str
    edge_type: str = Field(..., min_length=1, max_length=50)
    weight: float = Field(default=1.0, ge=0.0)
    description: str | None = None
    metadata_json: dict[str, Any] | None = None


class KnowledgeEdgeResponse(BaseModel):
    """Full knowledge edge response."""

    id: str
    source_id: str
    target_id: str
    edge_type: str
    weight: float
    description: str | None
    metadata_json: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeEdgeListResponse(BaseModel):
    """Paginated list of knowledge edges."""

    edges: list[KnowledgeEdgeResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Graph reasoning response schemas
# ---------------------------------------------------------------------------


class GraphPathStep(BaseModel):
    """One step in a graph path (node + incoming edge type)."""

    node_id: str
    node_slug: str | None
    node_name: str
    node_type: str
    edge_type: str | None = None  # None for the first node in the path


class GraphPathResponse(BaseModel):
    """Result of a shortest-path query between two nodes."""

    source_slug: str
    target_slug: str
    path_length: int
    path: list[GraphPathStep]


class GraphNeighborEntry(BaseModel):
    """A single neighbour in the result of a neighbour query."""

    node_id: str
    node_slug: str | None
    node_name: str
    node_type: str
    edge_type: str
    direction: str  # 'outgoing' | 'incoming'
    depth: int


class GraphNeighborsResponse(BaseModel):
    """Neighbours of a given node up to N hops."""

    center_node: KnowledgeNodeResponse
    neighbors: list[GraphNeighborEntry]
    total_neighbors: int


class GraphSubgraphResponse(BaseModel):
    """Subgraph induced by a set of node slugs."""

    nodes: list[KnowledgeNodeResponse]
    edges: list[KnowledgeEdgeResponse]


# ---------------------------------------------------------------------------
# Extraction request
# ---------------------------------------------------------------------------


class ExtractGraphRequest(BaseModel):
    """Request to auto-extract a knowledge graph from a wiki page."""

    wiki_page_id: str


# ---------------------------------------------------------------------------
# Knowledge Evolution Draft schemas
# ---------------------------------------------------------------------------


class KnowledgeDraftResponse(BaseModel):
    """Payload representing a proposed knowledge evolution draft."""

    id: str
    change_type: str
    status: str
    draft_data: dict[str, Any]
    source_info: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeDraftReview(BaseModel):
    """Request schema for HITL admin to approve/reject a proposed draft."""

    status: str = Field(..., description="Must be 'approved' or 'rejected'")
