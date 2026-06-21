"""Graph reasoning engine using NetworkX.

Loads the full KnowledgeNode / KnowledgeEdge data from PostgreSQL into an
in-memory NetworkX DiGraph and exposes higher-level reasoning primitives:

* find_path       — shortest causal path between two nodes
* get_neighbors   — BFS neighbourhood up to `depth` hops
* get_subgraph    — subgraph induced by a given set of node slugs
"""

from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

import networkx as nx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.graph import KnowledgeEdge, KnowledgeNode

logger = get_logger("graph_reasoner")


class GraphReasoner:
    """Higher-level reasoning over the knowledge graph using NetworkX.

    Includes a TTL cache for the in-memory graph to avoid rebuilding
    the full graph from PostgreSQL on every query.
    """

    _graph_cache: nx.DiGraph | None = None
    _cache_timestamp: float = 0.0
    _cache_lock = threading.Lock()
    _cache_ttl: int = 300  # 5 minutes TTL

    # ------------------------------------------------------------------
    # Graph construction
    # ------------------------------------------------------------------

    async def _get_cached_graph(self, db: AsyncSession) -> nx.DiGraph:
        """Return cached graph if fresh, otherwise rebuild."""
        now = time.time()
        if (
            self._graph_cache is not None
            and (now - self._cache_timestamp) < self._cache_ttl
        ):
            return self._graph_cache

        # Rebuild under lock to avoid concurrent rebuilds
        with self._cache_lock:
            # Double-check after acquiring lock
            if self._graph_cache is not None and (time.time() - self._cache_timestamp) < self._cache_ttl:
                return self._graph_cache

            self._graph_cache = await self._build_graph_impl(db)
            self._cache_timestamp = time.time()
            return self._graph_cache

    async def _build_graph_impl(self, db: AsyncSession) -> nx.DiGraph:
        """Load all nodes and edges from PostgreSQL into a NetworkX DiGraph.

        Node attributes: id, slug, name, node_type, description
        Edge attributes: edge_type, weight, description
        """
        g: nx.DiGraph = nx.DiGraph()

        # Load all nodes
        nodes_result = await db.execute(select(KnowledgeNode))
        nodes: list[KnowledgeNode] = list(nodes_result.scalars().all())

        for node in nodes:
            g.add_node(
                node.id,
                slug=node.slug or "",
                name=node.name,
                node_type=node.node_type,
                description=node.description or "",
            )

        # Build id-lookup by slug for path queries
        # (stored as graph attribute for convenience)
        g.graph["slug_to_id"] = {
            node.slug: node.id for node in nodes if node.slug
        }
        g.graph["id_to_node"] = {node.id: node for node in nodes}

        # Load all edges
        edges_result = await db.execute(select(KnowledgeEdge))
        edges: list[KnowledgeEdge] = list(edges_result.scalars().all())

        for edge in edges:
            # Only add edge if both endpoints are in the graph
            if edge.source_id in g and edge.target_id in g:
                g.add_edge(
                    edge.source_id,
                    edge.target_id,
                    id=edge.id,
                    edge_type=edge.edge_type,
                    weight=edge.weight,
                    description=edge.description or "",
                )

        logger.info(
            "graph_built",
            node_count=g.number_of_nodes(),
            edge_count=g.number_of_edges(),
        )
        return g

    # ------------------------------------------------------------------
    # Reasoning primitives
    # ------------------------------------------------------------------

    async def find_path(
        self,
        db: AsyncSession,
        source_slug: str,
        target_slug: str,
    ) -> list[dict[str, Any]]:
        """Find the shortest directed path between two nodes by slug.

        Returns a list of step dicts, each containing node metadata and
        the edge_type that connects the previous step to this one.

        Raises:
            ValueError: if either slug is unknown or no path exists.
        """
        g = await self._get_cached_graph(db)
        slug_to_id: dict[str, str] = g.graph.get("slug_to_id", {})

        source_id = slug_to_id.get(source_slug)
        if source_id is None and source_slug in g:
            source_id = source_slug

        target_id = slug_to_id.get(target_slug)
        if target_id is None and target_slug in g:
            target_id = target_slug

        if source_id is None:
            raise ValueError(f"Node slug not found: '{source_slug}'")
        if target_id is None:
            raise ValueError(f"Node slug not found: '{target_slug}'")

        try:
            path_ids: list[str] = nx.shortest_path(
                g, source=source_id, target=target_id
            )
        except nx.NetworkXNoPath:
            # Fallback: try undirected path so bidirectional relationships are found
            try:
                path_ids = nx.shortest_path(
                    g.to_undirected(), source=source_id, target=target_id
                )
                logger.info(
                    "graph_path_undirected_fallback",
                    source=source_slug,
                    target=target_slug,
                )
            except nx.NetworkXNoPath:
                raise ValueError(
                    f"No path (directed or undirected) from '{source_slug}' to '{target_slug}'"
                )
        except nx.NodeNotFound as exc:
            raise ValueError(str(exc)) from exc

        steps: list[dict[str, Any]] = []
        for i, node_id in enumerate(path_ids):
            node_attrs = g.nodes[node_id]
            edge_type: str | None = None
            if i > 0:
                prev_id = path_ids[i - 1]
                if g.has_edge(prev_id, node_id):
                    edge_data = g.edges[prev_id, node_id]
                    edge_type = edge_data.get("edge_type")
                elif g.has_edge(node_id, prev_id):
                    # Edge exists in the opposite direction — annotate for the user
                    edge_data = g.edges[node_id, prev_id]
                    raw_type = edge_data.get("edge_type") or "RELATED_TO"
                    edge_type = f"{raw_type} (ngược lại)"
                else:
                    edge_type = "RELATED_TO"

            steps.append(
                {
                    "node_id": node_id,
                    "node_slug": node_attrs.get("slug"),
                    "node_name": node_attrs.get("name"),
                    "node_type": node_attrs.get("node_type"),
                    "edge_type": edge_type,
                }
            )

        return steps


    async def get_neighbors(
        self,
        db: AsyncSession,
        node_slug: str,
        *,
        edge_types: list[str] | None = None,
        depth: int = 1,
    ) -> dict[str, Any]:
        """Return direct and multi-hop neighbours of a node.

        Args:
            db:         Async DB session.
            node_slug:  Slug of the centre node.
            edge_types: Optional filter — only traverse edges of these types.
            depth:      Maximum number of hops (BFS).

        Returns:
            dict with keys:
                node   – attributes of the centre node,
                neighbors – list of {node_id, node_slug, node_name, node_type,
                                      edge_type, direction, depth}

        Raises:
            ValueError: if the slug is unknown.
        """
        g = await self._get_cached_graph(db)
        slug_to_id: dict[str, str] = g.graph.get("slug_to_id", {})
        center_id = slug_to_id.get(node_slug)
        if center_id is None and node_slug in g:
            center_id = node_slug

        if center_id is None:
            raise ValueError(f"Node slug not found: '{node_slug}'")

        center_attrs = g.nodes[center_id]
        center_info: dict[str, Any] = {
            "node_id": center_id,
            **center_attrs,
        }

        # BFS over outgoing + incoming edges
        visited: set[str] = {center_id}
        frontier: deque[tuple[str, int]] = deque([(center_id, 0)])
        neighbor_list: list[dict[str, Any]] = []

        while frontier:
            current_id, current_depth = frontier.popleft()
            if current_depth >= depth:
                continue

            # Outgoing edges
            for _, nbr_id, edata in g.out_edges(current_id, data=True):
                etype = edata.get("edge_type", "")
                if edge_types and etype not in edge_types:
                    continue
                if nbr_id not in visited:
                    visited.add(nbr_id)
                    node_attrs = g.nodes[nbr_id]
                    neighbor_list.append(
                        {
                            "node_id": nbr_id,
                            "node_slug": node_attrs.get("slug"),
                            "node_name": node_attrs.get("name"),
                            "node_type": node_attrs.get("node_type"),
                            "edge_type": etype,
                            "direction": "outgoing",
                            "depth": current_depth + 1,
                        }
                    )
                    frontier.append((nbr_id, current_depth + 1))

            # Incoming edges
            for src_id, _, edata in g.in_edges(current_id, data=True):
                etype = edata.get("edge_type", "")
                if edge_types and etype not in edge_types:
                    continue
                if src_id not in visited:
                    visited.add(src_id)
                    node_attrs = g.nodes[src_id]
                    neighbor_list.append(
                        {
                            "node_id": src_id,
                            "node_slug": node_attrs.get("slug"),
                            "node_name": node_attrs.get("name"),
                            "node_type": node_attrs.get("node_type"),
                            "edge_type": etype,
                            "direction": "incoming",
                            "depth": current_depth + 1,
                        }
                    )
                    frontier.append((src_id, current_depth + 1))

        return {
            "node": center_info,
            "neighbors": neighbor_list,
        }

    async def get_subgraph(
        self,
        db: AsyncSession,
        node_slugs: list[str],
    ) -> dict[str, Any]:
        """Return the subgraph induced by the given node slugs.

        Only edges where both endpoints are in the requested set are included.

        Returns:
            dict with keys 'nodes' (list of node attr dicts) and
            'edges' (list of edge attr dicts).
        """
        g = await self._get_cached_graph(db)
        slug_to_id: dict[str, str] = g.graph.get("slug_to_id", {})

        node_ids: set[str] = set()
        for slug in node_slugs:
            nid = slug_to_id.get(slug)
            if nid:
                node_ids.add(nid)

        sub = g.subgraph(node_ids)

        nodes_out: list[dict[str, Any]] = []
        for nid, attrs in sub.nodes(data=True):
            nodes_out.append({"node_id": nid, **attrs})

        edges_out: list[dict[str, Any]] = []
        for src, tgt, edata in sub.edges(data=True):
            edges_out.append(
                {
                    "source_id": src,
                    "target_id": tgt,
                    **edata,
                }
            )

        return {"nodes": nodes_out, "edges": edges_out}

    async def get_graph_stats(self, db: AsyncSession) -> dict[str, Any]:
        """Compute basic graph statistics using NetworkX."""
        g = await self._get_cached_graph(db)
        node_count = g.number_of_nodes()
        edge_count = g.number_of_edges()
        avg_deg = (edge_count * 2.0 / node_count) if node_count > 0 else 0.0
        return {
            "node_count": node_count,
            "relationship_count": edge_count,
            "average_degree": avg_deg,
            "provider": "networkx"
        }

    async def get_node_degree(self, db: AsyncSession, slug: str) -> int:
        """Compute degree of a node using NetworkX."""
        g = await self._get_cached_graph(db)
        slug_to_id = g.graph.get("slug_to_id", {})
        node_id = slug_to_id.get(slug, slug)
        if node_id in g:
            return g.degree(node_id)
        return 0

    async def get_pagerank(self, db: AsyncSession) -> dict[str, float]:
        """Compute PageRank for all nodes using NetworkX."""
        g = await self._get_cached_graph(db)
        if g.number_of_nodes() == 0:
            return {}
        id_to_node = g.graph.get("id_to_node", {})
        try:
            pr = nx.pagerank(g, alpha=0.85)
        except Exception:
            return {
                id_to_node[node_id].slug if node_id in id_to_node else node_id: 1.0 / g.number_of_nodes()
                for node_id in g
            }
        return {
            id_to_node[node_id].slug if node_id in id_to_node else node_id: score
            for node_id, score in pr.items()
        }

    async def get_degree_centrality(self, db: AsyncSession) -> dict[str, float]:
        """Compute Degree Centrality for all nodes using NetworkX."""
        g = await self._get_cached_graph(db)
        if g.number_of_nodes() == 0:
            return {}
        id_to_node = g.graph.get("id_to_node", {})
        dc = nx.degree_centrality(g)
        return {
            id_to_node[node_id].slug if node_id in id_to_node else node_id: score
            for node_id, score in dc.items()
        }

    async def get_node_metrics(self, db: AsyncSession, slug: str) -> dict[str, Any]:
        """Get comprehensive analytics metrics for a specific node."""
        g = await self._get_cached_graph(db)
        slug_to_id = g.graph.get("slug_to_id", {})
        node_id = slug_to_id.get(slug, slug)
        if node_id not in g:
            return {}
        
        dc_scores = nx.degree_centrality(g)
        try:
            pr_scores = nx.pagerank(g, alpha=0.85)
        except Exception:
            pr_scores = {nid: 1.0 / g.number_of_nodes() for nid in g}
            
        dc = dc_scores.get(node_id, 0.0)
        pr = pr_scores.get(node_id, 0.0)
        
        return {
            "slug": slug,
            "degree": g.degree(node_id),
            "degree_centrality": dc,
            "pagerank": pr,
        }

