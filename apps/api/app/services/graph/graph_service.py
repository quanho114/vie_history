"""Graph service — CRUD for nodes/edges + LLM-based extraction."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.graph import KnowledgeEdge, KnowledgeNode
from app.services.llm.client import get_llm_client
from app.services.llm.json_parser import parse_llm_json

logger = get_logger("graph_service")

# ---------------------------------------------------------------------------
# System prompt for graph extraction
# ---------------------------------------------------------------------------

_EXTRACT_SYSTEM_PROMPT = (
    "You are a Vietnamese history expert. "
    "Extract a knowledge graph from the wiki page provided. "
    "Return pure JSON — no markdown fences, no extra text — with two keys:\n"
    '  "nodes": array of {node_type, name, slug, description},\n'
    '  "edges": array of {source_slug, target_slug, edge_type, description}.\n'
    "node_type must be one of: Event, Person, Organization, Location, Document, "
    "Agreement, Battle, Period, Concept.\n"
    "edge_type must be one of: PARTICIPATED_IN, LED_BY, HAPPENED_AT, "
    "HAPPENED_AFTER, CAUSED_BY, LED_TO, MENTIONED_IN, RELATED_TO, SIGNED_BY, OPPOSED.\n"
    "slug must be URL-friendly (lowercase, hyphens only)."
)


def _slugify(text: str) -> str:
    """Lightweight slug generator (ASCII fallback)."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:490]


class GraphService:
    """Business logic for knowledge graph node and edge management."""

    # ------------------------------------------------------------------
    # Node CRUD
    # ------------------------------------------------------------------

    async def get_nodes(
        self,
        db: AsyncSession,
        *,
        node_type: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[KnowledgeNode], int]:
        """Return a filtered, paginated list of nodes."""
        base_query = select(KnowledgeNode)
        count_query = select(func.count(KnowledgeNode.id))

        filters = []
        if node_type:
            filters.append(KnowledgeNode.node_type == node_type)
        if search:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    KnowledgeNode.name.ilike(pattern),
                    KnowledgeNode.description.ilike(pattern),
                )
            )

        for f in filters:
            base_query = base_query.where(f)
            count_query = count_query.where(f)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        result = await db.execute(
            base_query.order_by(KnowledgeNode.name.asc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_node_by_id(
        self, db: AsyncSession, node_id: str
    ) -> KnowledgeNode | None:
        """Fetch a node by UUID."""
        result = await db.execute(
            select(KnowledgeNode).where(KnowledgeNode.id == node_id)
        )
        return result.scalar_one_or_none()

    async def get_node_by_slug(
        self, db: AsyncSession, slug: str
    ) -> KnowledgeNode | None:
        """Fetch a node by slug."""
        result = await db.execute(
            select(KnowledgeNode).where(KnowledgeNode.slug == slug)
        )
        return result.scalar_one_or_none()

    async def create_node(
        self, db: AsyncSession, data: dict[str, Any]
    ) -> KnowledgeNode:
        """Persist a new knowledge node.

        Auto-generates slug from name if not provided.
        """
        if not data.get("slug") and data.get("name"):
            data["slug"] = _slugify(data["name"])

        node = KnowledgeNode(**data)
        db.add(node)
        await db.flush()
        await db.refresh(node)
        logger.info("knowledge_node_created", node_id=node.id, slug=node.slug)
        return node

    async def update_node(
        self, db: AsyncSession, node_id: str, data: dict[str, Any]
    ) -> KnowledgeNode:
        """Partially update a knowledge node.

        Raises:
            ValueError: if node not found.
        """
        node = await self.get_node_by_id(db, node_id)
        if node is None:
            raise ValueError(f"KnowledgeNode not found: {node_id}")

        for key, value in data.items():
            if value is not None:
                setattr(node, key, value)

        await db.flush()
        await db.refresh(node)
        logger.info("knowledge_node_updated", node_id=node_id)
        return node

    async def delete_node(self, db: AsyncSession, node_id: str) -> None:
        """Delete a node and its connected edges (cascade).

        Raises:
            ValueError: if node not found.
        """
        node = await self.get_node_by_id(db, node_id)
        if node is None:
            raise ValueError(f"KnowledgeNode not found: {node_id}")

        await db.delete(node)
        await db.flush()
        logger.info("knowledge_node_deleted", node_id=node_id)

    # ------------------------------------------------------------------
    # Edge CRUD
    # ------------------------------------------------------------------

    async def get_edges(
        self,
        db: AsyncSession,
        *,
        source_id: str | None = None,
        target_id: str | None = None,
        edge_type: str | None = None,
        page: int = 1,
        page_size: int = 100,
    ) -> tuple[list[KnowledgeEdge], int]:
        """Return a filtered, paginated list of edges."""
        base_query = select(KnowledgeEdge)
        count_query = select(func.count(KnowledgeEdge.id))

        filters = []
        if source_id:
            filters.append(KnowledgeEdge.source_id == source_id)
        if target_id:
            filters.append(KnowledgeEdge.target_id == target_id)
        if edge_type:
            filters.append(KnowledgeEdge.edge_type == edge_type)

        for f in filters:
            base_query = base_query.where(f)
            count_query = count_query.where(f)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        result = await db.execute(
            base_query.order_by(KnowledgeEdge.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def create_edge(
        self, db: AsyncSession, data: dict[str, Any]
    ) -> KnowledgeEdge:
        """Persist a new directed edge between two nodes."""
        edge = KnowledgeEdge(**data)
        db.add(edge)
        await db.flush()
        await db.refresh(edge)
        logger.info(
            "knowledge_edge_created",
            edge_id=edge.id,
            edge_type=edge.edge_type,
            source=edge.source_id,
            target=edge.target_id,
        )
        return edge

    async def _upsert_edge(
        self, db: AsyncSession, data: dict[str, Any]
    ) -> KnowledgeEdge:
        """Create or update an edge matched by source, target, and type."""
        result = await db.execute(
            select(KnowledgeEdge).where(
                KnowledgeEdge.source_id == data["source_id"],
                KnowledgeEdge.target_id == data["target_id"],
                KnowledgeEdge.edge_type == data["edge_type"],
            )
        )
        existing = result.scalar_one_or_none()
        if existing is None:
            return await self.create_edge(db, data)

        if data.get("description"):
            existing.description = data["description"]
        if data.get("metadata_json"):
            existing.metadata_json = data["metadata_json"]
        if data.get("weight") is not None:
            existing.weight = data["weight"]
        await db.flush()
        await db.refresh(existing)
        logger.info("knowledge_edge_upserted", edge_id=existing.id)
        return existing

    async def delete_edge(self, db: AsyncSession, edge_id: str) -> None:
        """Delete an edge by UUID.

        Raises:
            ValueError: if edge not found.
        """
        result = await db.execute(
            select(KnowledgeEdge).where(KnowledgeEdge.id == edge_id)
        )
        edge = result.scalar_one_or_none()
        if edge is None:
            raise ValueError(f"KnowledgeEdge not found: {edge_id}")

        await db.delete(edge)
        await db.flush()
        logger.info("knowledge_edge_deleted", edge_id=edge_id)

    # ------------------------------------------------------------------
    # LLM-based extraction
    # ------------------------------------------------------------------

    async def _upsert_node(
        self, db: AsyncSession, node_data: dict[str, Any]
    ) -> KnowledgeNode:
        """Create or return existing node matched by slug."""
        slug = node_data.get("slug") or _slugify(node_data.get("name", "unknown"))
        existing = await self.get_node_by_slug(db, slug)
        if existing:
            for key, value in node_data.items():
                if value is not None and key in {
                    "node_type",
                    "name",
                    "description",
                    "wiki_page_id",
                    "event_id",
                    "metadata_json",
                }:
                    setattr(existing, key, value)
            await db.flush()
            await db.refresh(existing)
            return existing

        node_data["slug"] = slug
        return await self.create_node(db, node_data)

    async def extract_graph_from_wiki_page(
        self,
        db: AsyncSession,
        wiki_page_id: str,
    ) -> tuple[list[KnowledgeNode], list[KnowledgeEdge]]:
        """Load a wiki page, call the LLM, and persist the extracted graph.

        Returns:
            (nodes, edges) tuple of persisted objects.

        Raises:
            ValueError: if the wiki page is not found or LLM returns invalid JSON.
        """
        # Direct import inside method to avoid circular imports at module level
        from app.models.timeline import HistoricalEvent  # noqa: PLC0415
        from app.models.wiki import WikiPage  # noqa: PLC0415

        page_result = await db.execute(select(WikiPage).where(WikiPage.id == wiki_page_id))
        wiki_page_obj = page_result.scalar_one_or_none()
        if wiki_page_obj is None:
            raise ValueError(f"WikiPage not found: {wiki_page_id}")

        wiki_title = wiki_page_obj.title or str(wiki_page_id)
        wiki_content = ""

        # Try to load from JSONB content dict first, then fall back to summary
        if wiki_page_obj.content and isinstance(wiki_page_obj.content, dict):
            wiki_content = "\n\n".join(
                str(v) for v in wiki_page_obj.content.values() if v
            )
        elif wiki_page_obj.summary:
            wiki_content = wiki_page_obj.summary

        content_snippet = wiki_content[:12_000]
        prompt = (
            f"Wiki page title: {wiki_title}\n\n"
            f"Content:\n{content_snippet}\n\n"
            "Extract a knowledge graph from this page. "
            "Return a JSON object with 'nodes' and 'edges' arrays."
        )

        llm = get_llm_client()
        logger.info(
            "graph_extraction_started",
            wiki_page_id=wiki_page_id,
            content_length=len(content_snippet),
        )
        extracted: dict = {"nodes": [], "edges": []}
        try:
            raw_response = await llm.generate(
                prompt,
                system=_EXTRACT_SYSTEM_PROMPT,
                max_tokens=4096,
            )
            # Parse JSON — use shared parser that handles markdown fences and conversational prefixes
            extracted = parse_llm_json(raw_response)
            if not isinstance(extracted, dict):
                extracted = {"nodes": [], "edges": []}
        except Exception as exc:
            logger.error(
                "graph_extraction_llm_error",
                wiki_page_id=wiki_page_id,
                error=str(exc),
            )

        nodes_data: list[dict] = extracted.get("nodes", [])
        edges_data: list[dict] = extracted.get("edges", [])

        if not nodes_data:
            nodes_data = [
                {
                    "node_type": "Event",
                    "name": wiki_page_obj.title,
                    "slug": wiki_page_obj.slug,
                    "description": wiki_page_obj.summary,
                }
            ]

        # Upsert nodes first, build slug→node index
        slug_to_node: dict[str, KnowledgeNode] = {}
        created_nodes: list[KnowledgeNode] = []
        for nd in nodes_data:
            node_slug = nd.get("slug") or _slugify(nd.get("name", "unknown"))
            event_result = await db.execute(
                select(HistoricalEvent).where(HistoricalEvent.slug == node_slug)
            )
            matching_event = event_result.scalar_one_or_none()
            node = await self._upsert_node(
                db,
                {
                    "node_type": nd.get("node_type", "Concept"),
                    "name": nd.get("name", "Unknown"),
                    "slug": node_slug,
                    "description": nd.get("description"),
                    "wiki_page_id": wiki_page_id,
                    "event_id": matching_event.id if matching_event else None,
                    "metadata_json": {
                        "source": "wiki_pipeline",
                        "wiki_page_slug": wiki_page_obj.slug,
                    },
                },
            )
            slug_to_node[node.slug or ""] = node
            created_nodes.append(node)

        # Create edges — silently skip if either end is missing
        created_edges: list[KnowledgeEdge] = []
        for ed in edges_data:
            src = slug_to_node.get(ed.get("source_slug", ""))
            tgt = slug_to_node.get(ed.get("target_slug", ""))
            if src is None or tgt is None:
                logger.warning(
                    "graph_extraction_edge_skipped",
                    source_slug=ed.get("source_slug"),
                    target_slug=ed.get("target_slug"),
                    reason="node not found",
                )
                continue

            edge = await self._upsert_edge(
                db,
                {
                    "source_id": src.id,
                    "target_id": tgt.id,
                    "edge_type": ed.get("edge_type", "RELATED_TO"),
                    "description": ed.get("description"),
                },
            )
            created_edges.append(edge)

        logger.info(
            "graph_extraction_done",
            wiki_page_id=wiki_page_id,
            nodes_created=len(created_nodes),
            edges_created=len(created_edges),
        )
        return created_nodes, created_edges
