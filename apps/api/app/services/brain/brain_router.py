"""Brain Router — fan-out query across wiki, timeline, and knowledge-graph stores in parallel."""

from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select, or_, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger("brain_router")

# ---------------------------------------------------------------------------
# Try to import GraphReasoner; if the module doesn't exist yet, degrade gracefully.
# ---------------------------------------------------------------------------
try:
    from app.services.graph.graph_reasoner import GraphReasoner  # type: ignore[import]
    _GRAPH_REASONER_AVAILABLE = True
except ImportError:
    _GRAPH_REASONER_AVAILABLE = False
    GraphReasoner = None  # type: ignore[assignment,misc]


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class BrainRouteResult:
    """Aggregated results from all activated brain search strategies."""

    intent: str
    routing_hints: dict = field(default_factory=dict)
    wiki_results: list[dict] = field(default_factory=list)
    timeline_results: list[dict] = field(default_factory=list)
    graph_results: dict = field(default_factory=lambda: {"nodes": [], "edges": [], "paths": []})
    vector_results: list[dict] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class BrainRouter:
    """
    Routes a query to the appropriate knowledge stores (wiki, timeline, graph)
    based on pre-computed routing hints and runs the searches in parallel.

    ``vector_results`` are *not* fetched here — they come from the existing
    SQLRetriever / hybrid-search pipeline in the orchestrator and are merged
    downstream by the ContextComposer.
    """

    async def route(
        self,
        db: AsyncSession,
        query: str,
        intent: str,
        routing_hints: dict,
        entities: list[str],
    ) -> BrainRouteResult:
        """Fan-out to activated brain stores in parallel; return merged result."""

        logger.info(
            "brain_router_route",
            intent=intent,
            routing_hints=routing_hints,
            entities=entities,
            query=query[:60],
        )

        # Async no-ops used when a brain store is not activated
        async def _empty_list() -> list:
            return []

        async def _empty_graph() -> dict:
            return {"nodes": [], "edges": [], "paths": []}

        # Build async tasks conditionally
        wiki_coro = (
            self._wiki_search(db, query, entities)
            if routing_hints.get("use_wiki")
            else _empty_list()
        )
        timeline_coro = (
            self._timeline_search(db, query, entities)
            if routing_hints.get("use_timeline")
            else _empty_list()
        )
        graph_coro = (
            self._graph_search(db, query, entities, intent)
            if routing_hints.get("use_graph") and _GRAPH_REASONER_AVAILABLE
            else _empty_graph()
        )

        wiki_res, timeline_res, graph_res = await asyncio.gather(
            wiki_coro,
            timeline_coro,
            graph_coro,
            return_exceptions=True,
        )

        # Gracefully handle per-task exceptions (tables may not exist yet)
        def _safe(val, default):
            if isinstance(val, BaseException):
                logger.warning("brain_router_task_failed", error=str(val))
                return default
            return val

        return BrainRouteResult(
            intent=intent,
            routing_hints=routing_hints,
            wiki_results=_safe(wiki_res, []),
            timeline_results=_safe(timeline_res, []),
            graph_results=_safe(graph_res, {"nodes": [], "edges": [], "paths": []}),
            vector_results=[],  # filled by orchestrator from existing RAG pipeline
            entities=entities,
        )

    # ------------------------------------------------------------------
    # Private search helpers
    # ------------------------------------------------------------------

    async def _wiki_search(
        self,
        db: AsyncSession,
        query: str,
        entities: list[str],
    ) -> list[dict]:
        """
        Full-text / ILIKE search against the ``wiki_pages`` table.

        Searches title and summary for the query terms and each extracted
        entity.  Returns up to 5 pages as plain dicts.
        """
        try:
            from app.models.wiki import WikiPage

            # Build search terms: individual words from query + entities
            terms = _tokenize(query) + [e.lower() for e in entities]
            # De-duplicate and cap to avoid massive OR chains
            terms = list(dict.fromkeys(terms))[:12]

            if not terms:
                return []

            # Build ILIKE filter for each term across title + summary
            conditions = []
            for term in terms:
                pattern = f"%{term}%"
                conditions.append(WikiPage.title.ilike(pattern))
                conditions.append(WikiPage.summary.ilike(pattern))

            stmt = (
                select(
                    WikiPage.slug,
                    WikiPage.title,
                    WikiPage.summary,
                    WikiPage.period,
                    WikiPage.event_type,
                    WikiPage.content,
                    WikiPage.start_year,
                    WikiPage.end_year,
                )
                .where(
                    WikiPage.status.in_(["published", "approved"]),
                    or_(*conditions),
                )
                .limit(5)
            )

            rows = (await db.execute(stmt)).fetchall()
            results = []
            for row in rows:
                results.append(
                    {
                        "slug": row.slug,
                        "title": row.title,
                        "summary": row.summary or "",
                        "period": row.period,
                        "event_type": row.event_type,
                        "content": row.content or {},
                        "start_year": row.start_year,
                        "end_year": row.end_year,
                    }
                )
            logger.info("wiki_search_results", count=len(results), query=query[:50])
            return results

        except Exception as exc:
            logger.warning("wiki_search_failed", error=str(exc))
            return []

    async def _timeline_search(
        self,
        db: AsyncSession,
        query: str,
        entities: list[str],
    ) -> list[dict]:
        """
        Search ``historical_events`` by name similarity and/or extracted year ranges.

        Returns up to 10 events sorted by ``start_year``.
        """
        try:
            from app.models.timeline import HistoricalEvent

            conditions = []

            # Year-range filter extracted from query text
            years = _extract_years(query)
            if years:
                start_y, end_y = years
                conditions.append(
                    or_(
                        HistoricalEvent.start_year.between(start_y - 1, end_y + 1),
                        HistoricalEvent.end_year.between(start_y - 1, end_y + 1),
                    )
                )

            # ILIKE on event_name for query terms + entities
            terms = _tokenize(query) + [e.lower() for e in entities]
            terms = list(dict.fromkeys(terms))[:10]
            for term in terms:
                conditions.append(HistoricalEvent.event_name.ilike(f"%{term}%"))

            if not conditions:
                return []

            stmt = (
                select(
                    HistoricalEvent.slug,
                    HistoricalEvent.event_name,
                    HistoricalEvent.start_year,
                    HistoricalEvent.end_year,
                    HistoricalEvent.period,
                    HistoricalEvent.summary,
                    HistoricalEvent.event_type,
                    HistoricalEvent.importance_level,
                )
                .where(or_(*conditions))
                .order_by(HistoricalEvent.start_year.asc().nulls_last())
                .limit(10)
            )

            rows = (await db.execute(stmt)).fetchall()
            results = []
            for row in rows:
                results.append(
                    {
                        "slug": row.slug,
                        "event_name": row.event_name,
                        "start_year": row.start_year,
                        "end_year": row.end_year,
                        "period": row.period,
                        "summary": row.summary or "",
                        "event_type": row.event_type,
                        "importance_level": row.importance_level,
                    }
                )
            logger.info("timeline_search_results", count=len(results), query=query[:50])
            return results

        except Exception as exc:
            logger.warning("timeline_search_failed", error=str(exc))
            return []

    async def _graph_search(
        self,
        db: AsyncSession,
        query: str,
        entities: list[str],
        intent: str,
    ) -> dict:
        """
        Query the knowledge graph for entities and their relationships.

        For ``cause_effect`` queries we attempt to find causal paths between
        the first two extracted entities.  Otherwise we return neighbours.
        """
        if not _GRAPH_REASONER_AVAILABLE or GraphReasoner is None:
            return {"nodes": [], "edges": [], "paths": []}

        try:
            reasoner = GraphReasoner()
            nodes: list[dict] = []
            edges: list[dict] = []
            paths: list[Any] = []

            # Map entity names to slugs since the reasoner queries by slug
            entity_slugs = [_slugify_basic(e) for e in entities if e]

            if intent == "cause_effect" and len(entity_slugs) >= 2:
                # Try causal path between first two entities
                try:
                    path_result = await reasoner.find_path(
                        db,
                        source_slug=entity_slugs[0],
                        target_slug=entity_slugs[1],
                    )
                    if path_result:
                        paths = [path_result]
                except Exception as path_exc:
                    logger.info("graph_search_path_not_found", error=str(path_exc))

            # Also get neighbors for all extracted entities
            for slug in entity_slugs[:4]:
                try:
                    neighbour_result = await reasoner.get_neighbors(db, node_slug=slug)
                    if neighbour_result:
                        # Extract the neighbors
                        nbrs = neighbour_result.get("neighbors", [])
                        for nbr in nbrs:
                            nodes.append({
                                "id": nbr.get("node_id"),
                                "slug": nbr.get("node_slug"),
                                "name": nbr.get("node_name"),
                                "node_type": nbr.get("node_type"),
                                "description": "",
                            })
                            edges.append({
                                "source_id": nbr.get("node_id") if nbr.get("direction") == "outgoing" else slug,
                                "target_id": slug if nbr.get("direction") == "outgoing" else nbr.get("node_id"),
                                "edge_type": nbr.get("edge_type"),
                            })
                        
                        # Also include the center node itself
                        center = neighbour_result.get("node", {})
                        if center:
                            nodes.append({
                                "id": center.get("node_id"),
                                "slug": center.get("slug"),
                                "name": center.get("name"),
                                "node_type": center.get("node_type"),
                                "description": center.get("description"),
                            })
                except Exception as nbr_exc:
                    logger.info("graph_search_neighbors_failed", slug=slug, error=str(nbr_exc))

            # De-duplicate nodes by id
            seen_ids: set = set()
            unique_nodes = []
            for node in nodes:
                nid = node.get("id")
                if nid and nid not in seen_ids:
                    seen_ids.add(nid)
                    unique_nodes.append(node)

            logger.info(
                "graph_search_results",
                nodes=len(unique_nodes),
                edges=len(edges),
                paths=len(paths),
            )
            return {"nodes": unique_nodes, "edges": edges, "paths": paths}

        except Exception as exc:
            logger.warning("graph_search_failed", error=str(exc))
            return {"nodes": [], "edges": [], "paths": []}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STOPWORDS = frozenset(
    [
        "là", "và", "của", "trong", "với", "về", "cho", "để", "không",
        "có", "một", "các", "những", "được", "đã", "này", "đó", "tại",
        "từ", "như", "hay", "hoặc", "thì", "mà", "khi", "vào", "ra",
        "the", "a", "an", "of", "in", "on", "at", "to", "for", "and", "or",
    ]
)

_YEAR_RE = re.compile(r"\b(1[4-9]\d{2}|20[1-9]\d|21[0-2]\d)\b")


def _tokenize(text: str) -> list[str]:
    """Split text into lowercase tokens, removing stopwords and short tokens."""
    tokens = re.findall(r"[\w\u00C0-\u024F\u1E00-\u1EFF]+", text.lower())
    return [t for t in tokens if len(t) >= 3 and t not in _STOPWORDS]


def _extract_years(text: str) -> tuple[int, int] | None:
    """Extract a year range from free text."""
    matches = _YEAR_RE.findall(text)
    if not matches:
        return None
    years = sorted(int(y) for y in matches)
    return (years[0], years[-1])


def _slugify_basic(text: str) -> str:
    """Simple ASCII slug — mirrors the pipeline's _slugify without a regex import."""
    import re

    text = text.lower().strip()
    replacements = {
        "à": "a", "á": "a", "ạ": "a", "ả": "a", "ã": "a",
        "â": "a", "ầ": "a", "ấ": "a", "ậ": "a", "ẩ": "a", "ẫ": "a",
        "ă": "a", "ằ": "a", "ắ": "a", "ặ": "a", "ẳ": "a", "ẵ": "a",
        "è": "e", "é": "e", "ẹ": "e", "ẻ": "e", "ẽ": "e",
        "ê": "e", "ề": "e", "ế": "e", "ệ": "e", "ể": "e", "ễ": "e",
        "ì": "i", "í": "i", "ị": "i", "ỉ": "i", "ĩ": "i",
        "ò": "o", "ó": "o", "ọ": "o", "ỏ": "o", "õ": "o",
        "ô": "o", "ồ": "o", "ố": "o", "ộ": "o", "ổ": "o", "ỗ": "o",
        "ơ": "o", "ờ": "o", "ớ": "o", "ợ": "o", "ở": "o", "ỡ": "o",
        "ù": "u", "ú": "u", "ụ": "u", "ủ": "u", "ũ": "u",
        "ư": "u", "ừ": "u", "ứ": "u", "ự": "u", "ử": "u", "ữ": "u",
        "ỳ": "y", "ý": "y", "ỵ": "y", "ỷ": "y", "ỹ": "y",
        "đ": "d",
    }
    for viet, ascii_ch in replacements.items():
        text = text.replace(viet, ascii_ch)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")[:450]
