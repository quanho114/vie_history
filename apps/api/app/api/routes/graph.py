"""Graph Brain API routes.

Prefix (set by main.py): /api/v1/graph
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.models.evolution import KnowledgeDraft
from app.schemas.graph import (
    ExtractGraphRequest,
    GraphNeighborEntry,
    GraphNeighborsResponse,
    GraphPathResponse,
    GraphPathStep,
    GraphSubgraphResponse,
    KnowledgeEdgeCreate,
    KnowledgeEdgeListResponse,
    KnowledgeEdgeResponse,
    KnowledgeNodeCreate,
    KnowledgeNodeListResponse,
    KnowledgeNodeResponse,
    KnowledgeNodeUpdate,
    KnowledgeDraftResponse,
    KnowledgeDraftReview,
)
from app.services.graph.graph_reasoner import GraphReasoner
from app.services.graph.graph_service import GraphService, _slugify
from app.services.graph.neo4j_service import Neo4jService

router = APIRouter()
_svc = GraphService()
_reasoner = GraphReasoner()


# ===========================================================================
# NODE ENDPOINTS
# ===========================================================================


@router.get("/nodes", response_model=KnowledgeNodeListResponse)
async def list_nodes(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    node_type: str | None = Query(default=None, description="Filter by node type"),
    search: str | None = Query(default=None, description="Search by name / description"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    """List knowledge graph nodes with optional type and text filters."""
    nodes, total = await _svc.get_nodes(
        db, node_type=node_type, search=search, page=page, page_size=page_size
    )
    return KnowledgeNodeListResponse(
        nodes=[KnowledgeNodeResponse.model_validate(n) for n in nodes],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/nodes/{node_id}", response_model=KnowledgeNodeResponse)
async def get_node(
    node_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Get a single knowledge node by UUID."""
    node = await _svc.get_node_by_id(db, node_id)
    if node is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node not found: {node_id}",
        )
    return KnowledgeNodeResponse.model_validate(node)


@router.post("/nodes", response_model=KnowledgeNodeResponse, status_code=status.HTTP_201_CREATED)
async def create_node(
    body: KnowledgeNodeCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a new knowledge graph node."""
    try:
        node = await _svc.create_node(db, body.model_dump(exclude_none=True))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    await db.commit()
    await db.refresh(node)
    return KnowledgeNodeResponse.model_validate(node)


@router.put("/nodes/{node_id}", response_model=KnowledgeNodeResponse)
async def update_node(
    node_id: str,
    body: KnowledgeNodeUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Partially update a knowledge node by UUID."""
    try:
        node = await _svc.update_node(
            db, node_id, body.model_dump(exclude_none=True)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    await db.commit()
    await db.refresh(node)
    return KnowledgeNodeResponse.model_validate(node)


@router.delete("/nodes/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(
    node_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Delete a knowledge node and its edges (cascade)."""
    try:
        await _svc.delete_node(db, node_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    await db.commit()


# ===========================================================================
# EDGE ENDPOINTS
# ===========================================================================


@router.get("/edges", response_model=KnowledgeEdgeListResponse)
async def list_edges(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    source_id: str | None = Query(default=None),
    target_id: str | None = Query(default=None),
    edge_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
):
    """List knowledge graph edges with optional filters."""
    edges, total = await _svc.get_edges(
        db,
        source_id=source_id,
        target_id=target_id,
        edge_type=edge_type,
        page=page,
        page_size=page_size,
    )
    return KnowledgeEdgeListResponse(
        edges=[KnowledgeEdgeResponse.model_validate(e) for e in edges],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/edges", response_model=KnowledgeEdgeResponse, status_code=status.HTTP_201_CREATED)
async def create_edge(
    body: KnowledgeEdgeCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Create a directed edge between two existing nodes."""
    try:
        edge = await _svc.create_edge(db, body.model_dump(exclude_none=True))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    await db.commit()
    await db.refresh(edge)
    return KnowledgeEdgeResponse.model_validate(edge)


@router.delete("/edges/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_edge(
    edge_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Delete a knowledge graph edge by UUID."""
    try:
        await _svc.delete_edge(db, edge_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    await db.commit()


# ===========================================================================
# GRAPH REASONING ENDPOINTS
# ===========================================================================


@router.get("/path", response_model=GraphPathResponse)
async def find_path(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    source: str = Query(..., description="Slug of the source node"),
    target: str = Query(..., description="Slug of the target node"),
):
    """Find the shortest causal/directed path between two nodes by slug."""
    try:
        steps = await _reasoner.find_path(db, source, target)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    return GraphPathResponse(
        source_slug=source,
        target_slug=target,
        path_length=len(steps) - 1,
        path=[GraphPathStep(**s) for s in steps],
    )


@router.get("/neighbors/{node_slug}", response_model=GraphNeighborsResponse)
async def get_neighbors(
    node_slug: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    depth: int = Query(default=1, ge=1, le=4, description="Number of hops"),
    edge_types: str | None = Query(
        default=None,
        description="Comma-separated edge types to filter (e.g. LED_BY,CAUSED_BY)",
    ),
):
    """Return the neighbourhood of a node up to `depth` hops.

    Traverses both outgoing and incoming edges.
    """
    parsed_edge_types: list[str] | None = None
    if edge_types:
        parsed_edge_types = [t.strip() for t in edge_types.split(",") if t.strip()]

    try:
        result = await _reasoner.get_neighbors(
            db, node_slug, edge_types=parsed_edge_types, depth=depth
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)
        ) from exc

    center_node_db = await _svc.get_node_by_slug(db, node_slug)
    if center_node_db is None:
        center_node_db = await _svc.get_node_by_id(db, node_slug)
        if center_node_db is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Node slug not found: {node_slug}",
            )

    neighbors = [GraphNeighborEntry(**n) for n in result["neighbors"]]
    return GraphNeighborsResponse(
        center_node=KnowledgeNodeResponse.model_validate(center_node_db),
        neighbors=neighbors,
        total_neighbors=len(neighbors),
    )


@router.get("/subgraph", response_model=GraphSubgraphResponse)
async def get_subgraph(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    nodes: str = Query(
        ...,
        description="Comma-separated node slugs (e.g. ho-chi-minh,dien-bien-phu)",
    ),
):
    """Return the subgraph induced by the given node slugs."""
    slug_list = [s.strip() for s in nodes.split(",") if s.strip()]
    if not slug_list:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one node slug must be provided.",
        )

    result = await _reasoner.get_subgraph(db, slug_list)

    # Convert raw dicts back to full DB objects for schema compliance
    node_responses: list[KnowledgeNodeResponse] = []
    for nd in result["nodes"]:
        node_db = await _svc.get_node_by_id(db, nd["node_id"])
        if node_db:
            node_responses.append(KnowledgeNodeResponse.model_validate(node_db))

    edge_responses: list[KnowledgeEdgeResponse] = []
    for ed in result["edges"]:
        edge_id = ed.get("id")
        if edge_id:
            from sqlalchemy import select  # noqa: PLC0415
            from app.models.graph import KnowledgeEdge  # noqa: PLC0415
            er = await db.execute(select(KnowledgeEdge).where(KnowledgeEdge.id == edge_id))
            edge_db = er.scalar_one_or_none()
            if edge_db:
                edge_responses.append(KnowledgeEdgeResponse.model_validate(edge_db))

    return GraphSubgraphResponse(nodes=node_responses, edges=edge_responses)


# ===========================================================================
# EXTRACTION ENDPOINT
# ===========================================================================


@router.post("/extract", status_code=status.HTTP_201_CREATED)
async def extract_graph(
    body: ExtractGraphRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Extract knowledge graph entities and relations from a wiki page via LLM."""
    try:
        nodes, edges = await _svc.extract_graph_from_wiki_page(
            db, wiki_page_id=body.wiki_page_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    await db.commit()

    return {
        "nodes_created": len(nodes),
        "edges_created": len(edges),
        "nodes": [KnowledgeNodeResponse.model_validate(n) for n in nodes],
        "edges": [KnowledgeEdgeResponse.model_validate(e) for e in edges],
    }


# ===========================================================================
# EVOLUTION / DRAFTS ENDPOINTS (HITL)
# ===========================================================================


@router.get("/drafts", response_model=list[KnowledgeDraftResponse])
async def list_drafts(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(default=None, description="Filter by status (pending, approved, rejected)"),
):
    """List proposed knowledge evolution drafts for HITL review."""
    query = select(KnowledgeDraft)
    if status:
        query = query.where(KnowledgeDraft.status == status)
    query = query.order_by(KnowledgeDraft.created_at.desc())

    result = await db.execute(query)
    drafts = result.scalars().all()
    return [KnowledgeDraftResponse.model_validate(d) for d in drafts]


@router.post("/drafts/{draft_id}/review", response_model=KnowledgeDraftResponse)
async def review_draft(
    draft_id: str,
    body: KnowledgeDraftReview,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Approve or reject a proposed knowledge draft.

    When approved, inserts/updates the entity or relation in both
    PostgreSQL and the Neo4j Graph DB dynamically.
    """
    if body.status not in ("approved", "rejected"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be either 'approved' or 'rejected'.",
        )

    # Fetch draft from PostgreSQL
    res = await db.execute(select(KnowledgeDraft).where(KnowledgeDraft.id == draft_id))
    draft = res.scalar_one_or_none()
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Draft not found: {draft_id}",
        )

    if draft.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Draft has already been reviewed (current status: {draft.status}).",
        )

    draft.status = body.status

    if body.status == "approved":
        # 1. Sync the proposed change to both databases based on change_type
        try:
            if draft.change_type == "add_node":
                data = draft.draft_data
                name = data.get("name")
                if not name:
                    raise ValueError("Node name is required in draft_data.")
                slug = data.get("slug") or _slugify(name)
                node_type = data.get("node_type", "Concept")
                desc = data.get("description", "")

                # PostgreSQL write
                await _svc._upsert_node(db, {
                    "node_type": node_type,
                    "name": name,
                    "slug": slug,
                    "description": desc,
                    "metadata_json": {"source": "hitl_evolution"},
                })

                # Neo4j write
                neo4j_svc = Neo4jService()
                await neo4j_svc.create_node(
                    node_type=node_type,
                    name=name,
                    slug=slug,
                    description=desc,
                    metadata_json={"source": "hitl_evolution"},
                )

            elif draft.change_type == "add_edge":
                data = draft.draft_data
                source_slug = data.get("source_slug")
                target_slug = data.get("target_slug")
                edge_type = data.get("edge_type", "RELATED_TO")
                desc = data.get("description", "")
                weight = float(data.get("weight", 1.0))

                if not source_slug or not target_slug:
                    raise ValueError("Both source_slug and target_slug are required in draft_data.")

                # Lookup nodes in PostgreSQL to get UUIDs
                src_node = await _svc.get_node_by_slug(db, source_slug)
                tgt_node = await _svc.get_node_by_slug(db, target_slug)

                if not src_node:
                    raise ValueError(f"Source node with slug '{source_slug}' does not exist in PostgreSQL.")
                if not tgt_node:
                    raise ValueError(f"Target node with slug '{target_slug}' does not exist in PostgreSQL.")

                # PostgreSQL write
                await _svc._upsert_edge(db, {
                    "source_id": src_node.id,
                    "target_id": tgt_node.id,
                    "edge_type": edge_type,
                    "description": desc,
                    "weight": weight,
                })

                # Neo4j write
                neo4j_svc = Neo4jService()
                await neo4j_svc.create_edge(
                    source_slug=source_slug,
                    target_slug=target_slug,
                    edge_type=edge_type,
                    description=desc,
                    weight=weight,
                )

            elif draft.change_type == "update_node":
                data = draft.draft_data
                slug = data.get("slug")
                if not slug:
                    raise ValueError("Node slug is required in draft_data for updates.")

                # Retrieve existing node in PostgreSQL
                node_db = await _svc.get_node_by_slug(db, slug)
                if not node_db:
                    raise ValueError(f"Node with slug '{slug}' does not exist in PostgreSQL.")

                # Update Postgres properties
                update_payload = {}
                if "name" in data:
                    update_payload["name"] = data["name"]
                if "description" in data:
                    update_payload["description"] = data["description"]
                if "node_type" in data:
                    update_payload["node_type"] = data["node_type"]

                await _svc.update_node(db, node_db.id, update_payload)

                # Update Neo4j properties
                neo4j_svc = Neo4jService()
                await neo4j_svc.create_node(
                    node_type=data.get("node_type") or node_db.node_type,
                    name=data.get("name") or node_db.name,
                    slug=slug,
                    description=data.get("description") or node_db.description,
                )

            elif draft.change_type == "contradiction":
                # Handle contradiction log by updating status in Postgres, no new nodes
                logger.info("hitl_contradiction_approved", draft_id=draft_id)
            else:
                raise ValueError(f"Unsupported change_type for approval: {draft.change_type}")

        except Exception as exc:
            db.rollback()
            logger.error("hitl_draft_approval_failed", draft_id=draft_id, error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Failed to synchronize approved draft to databases: {str(exc)}",
            )

    # Save reviewed status in PostgreSQL
    await db.commit()
    await db.refresh(draft)
    return KnowledgeDraftResponse.model_validate(draft)

