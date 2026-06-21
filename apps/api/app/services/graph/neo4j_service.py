"""Neo4j service for persistent, multi-hop relationship and causal graph reasoning."""

from __future__ import annotations

import json
import re
from typing import Any

from neo4j import AsyncGraphDatabase

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("neo4j_service")

VALID_NODE_TYPES = {
    "Event",
    "Person",
    "Organization",
    "Location",
    "Document",
    "Agreement",
    "Battle",
    "Period",
    "Concept",
}

VALID_EDGE_TYPES = {
    "PARTICIPATED_IN",
    "LED_BY",
    "HAPPENED_AT",
    "HAPPENED_AFTER",
    "CAUSED_BY",
    "LED_TO",
    "MENTIONED_IN",
    "RELATED_TO",
    "SIGNED_BY",
    "OPPOSED",
}


def _slugify(text: str) -> str:
    """Lightweight slug generator (ASCII fallback)."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:490]


def _clean_properties(props: dict[str, Any]) -> dict[str, Any]:
    """Parse JSON strings back to dict where appropriate."""
    res = dict(props)
    if "metadata_json" in res and isinstance(res["metadata_json"], str):
        try:
            res["metadata_json"] = json.loads(res["metadata_json"])
        except Exception:
            pass
    return res


class Neo4jService:
    """Business logic for Neo4j Graph Database interactions."""

    def __init__(
        self,
        uri: str | None = None,
        user: str | None = None,
        password: str | None = None,
    ):
        self.uri = uri or settings.NEO4J_URL
        self.user = user or settings.NEO4J_USER
        self.password = password or settings.NEO4J_PASSWORD
        self._driver = None

    def connect(self) -> None:
        """Initialize the Neo4j client driver."""
        if not self._driver:
            self._driver = AsyncGraphDatabase.driver(
                self.uri, auth=(self.user, self.password)
            )
            logger.info("neo4j_driver_initialized", uri=self.uri)

    async def close(self) -> None:
        """Close the Neo4j client driver."""
        if self._driver:
            await self._driver.close()
            self._driver = None
            logger.info("neo4j_driver_closed")

    async def check_connection(self) -> bool:
        """Check if Neo4j service is healthy and connected."""
        self.connect()
        try:
            async with self._driver.session() as session:
                result = await session.run("RETURN 1 AS val")
                record = await result.single()
                return record is not None and record["val"] == 1
        except Exception as exc:
            logger.error("neo4j_connection_check_failed", error=str(exc))
            return False

    async def clear_database(self) -> None:
        """Wipe all nodes and edges (useful for migrations and tests)."""
        self.connect()
        async with self._driver.session() as session:
            await session.run("MATCH (n) DETACH DELETE n")
            logger.info("neo4j_database_cleared")

    # ------------------------------------------------------------------
    # Node Management
    # ------------------------------------------------------------------

    async def create_node(
        self,
        node_type: str,
        name: str,
        slug: str | None = None,
        description: str | None = None,
        wiki_page_id: str | None = None,
        event_id: str | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create or update a node in Neo4j."""
        self.connect()
        if node_type not in VALID_NODE_TYPES:
            logger.warning("neo4j_invalid_node_type", node_type=node_type)
            node_type = "Concept"

        if not slug:
            slug = _slugify(name)

        # Standard Cypher MERGE with validated node label formatting
        query = (
            f"MERGE (n:KnowledgeNode {{slug: $slug}}) "
            f"ON CREATE SET n.created_at = timestamp() "
            f"ON MATCH SET n.updated_at = timestamp() "
            f"SET n:{node_type} "
            f"SET n.name = $name, "
            f"    n.node_type = $node_type, "
            f"    n.description = $description, "
            f"    n.wiki_page_id = $wiki_page_id, "
            f"    n.event_id = $event_id, "
            f"    n.metadata_json = $metadata_json "
            f"RETURN n"
        )

        async with self._driver.session() as session:
            result = await session.run(
                query,
                slug=slug,
                name=name,
                node_type=node_type,
                description=description or "",
                wiki_page_id=str(wiki_page_id) if wiki_page_id else None,
                event_id=str(event_id) if event_id else None,
                metadata_json=json.dumps(metadata_json) if metadata_json else "{}",
            )
            record = await result.single()
            if record:
                node = record["n"]
                return _clean_properties(dict(node.items()))
            raise ValueError(f"Failed to create node: {name}")

    async def get_node_by_slug(self, slug: str) -> dict[str, Any] | None:
        """Fetch node properties by slug."""
        self.connect()
        query = "MATCH (n:KnowledgeNode {slug: $slug}) RETURN n"
        async with self._driver.session() as session:
            result = await session.run(query, slug=slug)
            record = await result.single()
            if record:
                return _clean_properties(dict(record["n"].items()))
            return None

    async def delete_node(self, slug: str) -> None:
        """Delete a node and cascade connected relationships."""
        self.connect()
        query = "MATCH (n:KnowledgeNode {slug: $slug}) DETACH DELETE n"
        async with self._driver.session() as session:
            await session.run(query, slug=slug)
            logger.info("neo4j_node_deleted", slug=slug)

    # ------------------------------------------------------------------
    # Edge Management
    # ------------------------------------------------------------------

    async def create_edge(
        self,
        source_slug: str,
        target_slug: str,
        edge_type: str,
        description: str | None = None,
        weight: float = 1.0,
    ) -> dict[str, Any]:
        """Create a directed relationship between two nodes."""
        self.connect()
        if edge_type not in VALID_EDGE_TYPES:
            logger.warning("neo4j_invalid_edge_type", edge_type=edge_type)
            edge_type = "RELATED_TO"

        # standard Cypher with dynamic relationship labels validated safely
        query = (
            f"MATCH (src:KnowledgeNode {{slug: $source_slug}}) "
            f"MATCH (tgt:KnowledgeNode {{slug: $target_slug}}) "
            f"MERGE (src)-[r:{edge_type}]->(tgt) "
            f"SET r.description = $description, "
            f"    r.edge_type = $edge_type, "
            f"    r.weight = $weight, "
            f"    r.updated_at = timestamp() "
            f"RETURN r"
        )

        async with self._driver.session() as session:
            result = await session.run(
                query,
                source_slug=source_slug,
                target_slug=target_slug,
                edge_type=edge_type,
                description=description or "",
                weight=weight,
            )
            record = await result.single()
            if record:
                return dict(record["r"].items())
            raise ValueError(
                f"Failed to create edge {edge_type} from {source_slug} to {target_slug}"
            )

    async def delete_edge(
        self, source_slug: str, target_slug: str, edge_type: str
    ) -> None:
        """Delete a relationship between two nodes."""
        self.connect()
        if edge_type not in VALID_EDGE_TYPES:
            edge_type = "RELATED_TO"
        query = (
            f"MATCH (src:KnowledgeNode {{slug: $source_slug}})-[r:{edge_type}]->(tgt:KnowledgeNode {{slug: $target_slug}}) "
            f"DELETE r"
        )
        async with self._driver.session() as session:
            await session.run(
                query, source_slug=source_slug, target_slug=target_slug
            )
            logger.info("neo4j_edge_deleted", src=source_slug, tgt=target_slug, type=edge_type)

    # ------------------------------------------------------------------
    # Graph Reasoning & Multi-Hop Traversal Primitives
    # ------------------------------------------------------------------

    async def find_path(
        self, source_slug: str, target_slug: str
    ) -> list[dict[str, Any]]:
        """Find the shortest path (causal/temporal chain) between two nodes."""
        self.connect()
        query = (
            "MATCH p = shortestPath((src:KnowledgeNode {slug: $source_slug})-[*..5]-(tgt:KnowledgeNode {slug: $target_slug})) "
            "RETURN p"
        )
        async with self._driver.session() as session:
            result = await session.run(
                query, source_slug=source_slug, target_slug=target_slug
            )
            record = await result.single()
            if not record:
                # Undirected or fallback to 1-hop relation search
                return []

            path = record["p"]
            steps = []
            nodes = path.nodes
            relationships = path.relationships

            for i, n in enumerate(nodes):
                edge_type = None
                if i > 0:
                    rel = relationships[i - 1]
                    edge_type = rel.type
                    # If this relation flows in reverse, annotate it
                    if rel.start_node.id != nodes[i - 1].id:
                        edge_type = f"{edge_type} (ngược lại)"

                steps.append(
                    {
                        "node_slug": n["slug"],
                        "node_name": n["name"],
                        "node_type": n["node_type"],
                        "edge_type": edge_type,
                    }
                )
            return steps

    async def get_neighbors(
        self, node_slug: str, depth: int = 1
    ) -> dict[str, Any]:
        """Fetch all neighbors of a node up to a certain depth."""
        self.connect()
        if depth > 3:
            depth = 3  # cap depth to prevent performance issues

        query = (
            f"MATCH (center:KnowledgeNode {{slug: $node_slug}}) "
            f"MATCH p = (center)-[*1..{depth}]-(neighbor:KnowledgeNode) "
            f"RETURN p"
        )

        async with self._driver.session() as session:
            result = await session.run(query, node_slug=node_slug)
            center_info = await self.get_node_by_slug(node_slug)
            if not center_info:
                raise ValueError(f"Node slug not found: '{node_slug}'")

            neighbors = {}
            async for record in result:
                path = record["p"]
                relationships = path.relationships
                nodes = path.nodes

                current_node = center_info
                for idx, rel in enumerate(relationships):
                    node_a = nodes[idx]
                    node_b = nodes[idx + 1]

                    target_node = node_b if node_a["slug"] == current_node["slug"] else node_a
                    direction = "outgoing" if rel.start_node.id == node_a.id else "incoming"

                    neighbor_slug = target_node["slug"]
                    if neighbor_slug not in neighbors:
                        neighbors[neighbor_slug] = {
                            "node_slug": neighbor_slug,
                            "node_name": target_node["name"],
                            "node_type": target_node["node_type"],
                            "edge_type": rel.type,
                            "direction": direction,
                            "depth": idx + 1,
                        }
            return {
                "node": center_info,
                "neighbors": list(neighbors.values()),
            }

    async def get_subgraph(self, node_slugs: list[str]) -> dict[str, Any]:
        """Fetch a subgraph induced by specific node slugs."""
        self.connect()
        query = (
            "MATCH (n:KnowledgeNode) WHERE n.slug IN $node_slugs "
            "OPTIONAL MATCH (n)-[r]->(m:KnowledgeNode) WHERE m.slug IN $node_slugs "
            "RETURN n, r, m"
        )
        async with self._driver.session() as session:
            result = await session.run(query, node_slugs=node_slugs)
            nodes = {}
            edges = []

            async for record in result:
                n = record["n"]
                if n:
                    nodes[n["slug"]] = _clean_properties(dict(n.items()))
                r = record["r"]
                m = record["m"]
                if r and m:
                    edges.append(
                        {
                            "source_slug": n["slug"],
                            "target_slug": m["slug"],
                            "edge_type": r.type,
                            "description": r.get("description", ""),
                            "weight": r.get("weight", 1.0),
                        }
                    )
            return {
                "nodes": list(nodes.values()),
                "edges": edges,
            }

    async def get_graph_stats(self) -> dict[str, Any]:
        """Fetch basic graph statistics using Cypher."""
        self.connect()
        try:
            async with self._driver.session() as session:
                node_res = await session.run("MATCH (n:KnowledgeNode) RETURN count(n) as count")
                node_record = await node_res.single()
                node_count = node_record["count"] if node_record else 0

                rel_res = await session.run("MATCH ()-[r]->() RETURN count(r) as count")
                rel_record = await rel_res.single()
                rel_count = rel_record["count"] if rel_record else 0

                avg_deg = (rel_count * 2.0 / node_count) if node_count > 0 else 0.0

                return {
                    "node_count": node_count,
                    "relationship_count": rel_count,
                    "average_degree": avg_deg,
                    "provider": "neo4j"
                }
        except Exception as exc:
            logger.error("neo4j_get_graph_stats_failed", error=str(exc))
            return {
                "node_count": 0,
                "relationship_count": 0,
                "average_degree": 0.0,
                "provider": "neo4j",
                "error": str(exc)
            }

    async def get_node_degree(self, slug: str) -> int:
        """Fetch degree of a specific node."""
        self.connect()
        query = "MATCH (n:KnowledgeNode {slug: $slug}) RETURN size((n)--()) as degree"
        try:
            async with self._driver.session() as session:
                res = await session.run(query, slug=slug)
                record = await res.single()
                return record["degree"] if record else 0
        except Exception as exc:
            logger.error("neo4j_get_node_degree_failed", slug=slug, error=str(exc))
            return 0

