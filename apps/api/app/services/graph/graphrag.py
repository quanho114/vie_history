"""GraphRAG: Knowledge graph-enhanced retrieval beyond simple neighbor lookup.

GraphRAG improvements over current implementation:
1. Entity-centric retrieval: Find documents containing specific entities
2. Relationship-aware search: Use edge types to guide retrieval
3. Multi-hop reasoning: Traverse graph for connected entity context
4. Community detection: Use graph communities for document clustering
5. Local vs Global search: Different strategies for different query types

Reference: "From Local to Global: A GraphRAG Approach to Query-Focused Summarization"
(Microsoft Research, 2024)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from app.core.logging import get_logger
from app.services.graph.neo4j_service import Neo4jService

logger = get_logger("graphrag")


@dataclass
class GraphRAGResult:
    """Result of a GraphRAG retrieval operation."""
    entities: list[dict[str, Any]] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    community_context: str = ""
    document_ids: list[str] = field(default_factory=list)
    reasoning_chain: list[str] = field(default_factory=list)
    chunks: list[dict[str, Any]] = field(default_factory=list)


class GraphRAGService:
    """
    GraphRAG: Hybrid knowledge graph + vector retrieval.

    Supports two search modes:
    - Local: Entity-centric retrieval for specific people/events
    - Global: Community-based summarization for broad topics
    """

    def __init__(
        self,
        neo4j_service: Neo4jService | None = None,
        vector_search: "VectorSearch | None" = None,
        query_service: "QueryService | None" = None,
    ):
        self._neo4j = neo4j_service or Neo4jService()
        self._vector_search = vector_search
        self._query_service = query_service

    @property
    def neo4j(self) -> Neo4jService:
        return self._neo4j

    @property
    def vector_search(self):
        """Lazy-load VectorSearch to avoid circular imports."""
        if self._vector_search is None:
            from app.services.retrieval.vector_search import VectorSearch
            self._vector_search = VectorSearch()
        return self._vector_search

    @property
    def query_service(self):
        """Lazy-load QueryService to avoid circular imports."""
        if self._query_service is None:
            from app.services.retrieval.query_service import QueryService
            self._query_service = QueryService()
        return self._query_service

    async def local_search(
        self,
        query: str,
        entities: list[str] | None = None,
        depth: int = 2,
        top_k: int = 5,
    ) -> GraphRAGResult:
        """
        Local GraphRAG search — entity-centric.

        1. Extract/find entities from query
        2. Get entity neighborhoods (multi-hop)
        3. Get documents containing these entities
        4. Synthesize with graph context
        """
        # 1. Find entities if not provided
        if not entities:
            entities = await self._extract_entities(query)

        if not entities:
            # Fallback to pure vector
            docs = await self.vector_search.search(query, top_k=top_k)
            return GraphRAGResult(
                entities=[],
                relationships=[],
                community_context="",
                document_ids=[d.get("document_id") for d in docs if d.get("document_id")],
                reasoning_chain=["No entities found, used vector search"],
                chunks=docs,
            )

        # 2. Multi-hop entity traversal
        all_entities = []
        all_relationships = []
        visited: set[str] = set()

        for entity in entities:
            neighborhood = await self._traverse_entity(
                entity,
                depth=depth,
                visited=visited,
            )
            all_entities.extend(neighborhood.get("entities", []))
            all_relationships.extend(neighborhood.get("relationships", []))

        # 3. Get documents containing these entities
        entity_slugs = [e.get("slug") for e in all_entities if e.get("slug")]
        doc_ids = await self._get_documents_for_entities(entity_slugs)

        # 4. Score documents by graph relevance
        chunks = await self._get_graph_boosted_chunks(
            query=query,
            entity_slugs=entity_slugs,
            graph_entities=all_entities,
            graph_relationships=all_relationships,
            top_k=top_k,
        )

        # 5. Generate reasoning chain
        reasoning_chain = [
            f"Extracted entities: {entities}",
            f"Expanded to {len(all_entities)} related entities via {depth}-hop traversal",
            f"Found {len(all_relationships)} relationships",
            f"Identified {len(doc_ids)} source documents",
        ]

        logger.info(
            "graphrag_local_search",
            query=query[:50],
            entities=len(entities),
            expanded_entities=len(all_entities),
            relationships=len(all_relationships),
            documents=len(doc_ids),
        )

        return GraphRAGResult(
            entities=all_entities[:20],  # Cap for context window
            relationships=all_relationships[:30],
            community_context="",  # Not used in local search
            document_ids=doc_ids,
            reasoning_chain=reasoning_chain,
            chunks=chunks,
        )

    async def global_search(
        self,
        query: str,
        top_k_communities: int = 3,
    ) -> GraphRAGResult:
        """
        Global GraphRAG search — community-based summarization.

        For broad queries (summaries, comparisons), find the most relevant
        graph communities and use their descriptions for context.

        1. Determine relevant communities via entity coverage
        2. Get community-level descriptions
        3. Generate meta-answer from community context
        """
        # 1. Get community statistics
        communities = await self._get_communities()

        # 2. Score communities by relevance to query
        scored_communities = []
        for community in communities:
            community_entities = await self._get_community_entities(community["id"])

            # Score based on entity name match with query
            entity_names = " ".join([e.get("name", "") for e in community_entities])
            # Simple keyword overlap scoring
            overlap = sum(
                1 for kw in query.lower().split()
                if kw in entity_names.lower()
            )

            scored_communities.append({
                "community": community,
                "entities": community_entities,
                "score": overlap,
                "entity_count": len(community_entities),
            })

        scored_communities.sort(key=lambda x: x["score"], reverse=True)
        top_communities = scored_communities[:top_k_communities]

        # 3. Build community context
        community_descriptions = []
        for sc in top_communities:
            community = sc["community"]
            entities = sc["entities"]

            desc = f"""Nhóm sự kiện: {community.get('name', 'Unknown')}
Số thực thể: {sc['entity_count']}
Thực thể chính: {', '.join([e.get('name', '') for e in entities[:5] if e.get('name')])}
Mô tả: {community.get('description', '')}"""
            community_descriptions.append(desc)

        community_context = "\n\n".join(community_descriptions)

        # 4. Get documents from top communities
        all_doc_ids: set[str] = set()
        for sc in top_communities:
            doc_ids = await self._get_documents_for_entities(
                [e.get("slug") for e in sc["entities"] if e.get("slug")]
            )
            all_doc_ids.update(doc_ids)

        reasoning_chain = [
            f"Identified {len(communities)} communities in knowledge graph",
            f"Selected top {top_k_communities} communities based on query relevance",
            f"Community context includes {sum(sc['entity_count'] for sc in top_communities)} entities",
            f"Found {len(all_doc_ids)} documents from selected communities",
        ]

        logger.info(
            "graphrag_global_search",
            query=query[:50],
            communities_found=len(communities),
            communities_selected=top_k_communities,
            documents=len(all_doc_ids),
        )

        return GraphRAGResult(
            entities=[e for sc in top_communities for e in sc["entities"][:5]],
            relationships=[],
            community_context=community_context,
            document_ids=list(all_doc_ids)[:10],
            reasoning_chain=reasoning_chain,
        )

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> GraphRAGResult:
        """
        Hybrid GraphRAG: combine graph context with vector search.

        1. Extract entities from query
        2. Get graph context (entities, relationships)
        3. Run vector search
        4. Score by graph relevance
        5. Return enriched results
        """
        # Get graph context
        graph_context = await self._get_graph_context(query)

        # Run hybrid vector search
        try:
            chunks = await self.query_service.hybrid_search(
                query=query,
                top_k=top_k,
                filters=filters,
            )
        except Exception:
            chunks = []

        # Score documents by graph relevance
        scored_chunks = self._score_by_graph_relevance(
            chunks=chunks,
            graph_context=graph_context,
        )

        return GraphRAGResult(
            entities=graph_context.get("entities", []),
            relationships=graph_context.get("relationships", []),
            document_ids=[c.get("document_id") for c in scored_chunks if c.get("document_id")],
            reasoning_chain=[
                f"Found {len(graph_context.get('entities', []))} related entities",
                f"Found {len(graph_context.get('relationships', []))} relationships",
                f"Retrieved {len(chunks)} document chunks",
                f"Scored by graph relevance",
            ],
            chunks=scored_chunks,
        )

    async def _extract_entities(self, query: str) -> list[str]:
        """Extract entities from query using LLM."""
        llm = get_llm_client()

        prompt = f"""Trích xuất các thực thể lịch sử (nhân vật, sự kiện, địa điểm, tổ chức) từ câu hỏi:

Câu hỏi: {query}

Trả về danh sách tên thực thể, mỗi tên trên một dòng. Nếu không có thực thể, trả về dòng trống."""

        try:
            response = await llm.generate(prompt, max_tokens=100)
            entities = [
                line.strip()
                for line in response.strip().split("\n")
                if line.strip() and len(line.strip()) > 2
            ]
            return entities
        except Exception:
            return []

    async def _traverse_entity(
        self,
        entity_slug: str,
        depth: int,
        visited: set[str],
    ) -> dict[str, Any]:
        """Multi-hop entity traversal from Neo4j."""
        if depth == 0 or entity_slug in visited:
            return {"entities": [], "relationships": []}

        visited.add(entity_slug)
        entities = []
        relationships = []

        # Get current entity
        try:
            current = await self.neo4j.get_node_by_slug(entity_slug)
            if current:
                entities.append(current)
        except Exception:
            pass

        # Get neighbors
        try:
            neighbors_result = await self.neo4j.get_neighbors(entity_slug, depth=1)
            neighbors = neighbors_result.get("neighbors", [])

            for neighbor in neighbors:
                neighbor_slug = neighbor.get("node_slug")
                if neighbor_slug and neighbor_slug not in visited:
                    entities.append(neighbor)
                    relationships.append({
                        "source": entity_slug,
                        "target": neighbor_slug,
                        "type": neighbor.get("edge_type", ""),
                    })

                    if depth > 1:
                        # Recurse
                        sub = await self._traverse_entity(
                            neighbor_slug, depth - 1, visited
                        )
                        entities.extend(sub.get("entities", []))
                        relationships.extend(sub.get("relationships", []))
        except Exception:
            pass

        return {"entities": entities, "relationships": relationships}

    async def _get_graph_context(self, query: str) -> dict[str, Any]:
        """Get graph context relevant to the query."""
        try:
            entities = await self._extract_entities(query)
            if not entities:
                return {"entities": [], "relationships": []}

            # Get neighbors for top entities
            all_entities = []
            all_relationships = []

            for entity_name in entities[:5]:
                from app.services.graph.graph_service import _slugify
                slug = _slugify(entity_name)
                try:
                    neighbors_result = await self.neo4j.get_neighbors(slug, depth=1)
                    neighbors = neighbors_result.get("neighbors", [])
                    all_entities.append(neighbors_result.get("node", {}))
                    all_relationships.extend(neighbors)
                except Exception:
                    pass

            return {
                "entities": all_entities[:10],
                "relationships": all_relationships[:20],
            }
        except Exception:
            return {"entities": [], "relationships": []}

    def _score_by_graph_relevance(
        self,
        chunks: list[dict[str, Any]],
        graph_context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Boost chunks that mention graph entities."""
        entity_names = {
            e.get("name", "").lower()
            for e in graph_context.get("entities", [])
        }
        relationship_types = {
            r.get("type", "").lower()
            for r in graph_context.get("relationships", [])
        }

        scored = []
        for chunk in chunks:
            chunk = dict(chunk)  # Copy to avoid mutation
            content = chunk.get("content", "").lower()
            graph_boost = 0.0

            for name in entity_names:
                if name and name in content:
                    graph_boost += 0.1

            for rel_type in relationship_types:
                if rel_type and rel_type in content:
                    graph_boost += 0.05

            chunk["graph_relevance_score"] = min(graph_boost, 0.5)
            # Combine with existing score
            chunk["combined_score"] = (
                chunk.get("rerank_score", 0) +
                chunk.get("score", 0) +
                chunk["graph_relevance_score"]
            )
            scored.append(chunk)

        # Re-rank by combined score
        scored.sort(
            key=lambda c: c.get("combined_score", 0),
            reverse=True,
        )
        return scored

    async def _get_graph_boosted_chunks(
        self,
        query: str,
        entity_slugs: list[str],
        graph_entities: list[dict[str, Any]],
        graph_relationships: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Get chunks boosted by graph relevance."""
        # First get chunks from vector search
        chunks = await self.vector_search.search(query, top_k=top_k * 2)

        # Build graph context for scoring
        graph_context = {
            "entities": graph_entities,
            "relationships": graph_relationships,
        }

        # Score by graph relevance
        scored = self._score_by_graph_relevance(chunks, graph_context)
        return scored[:top_k]

    async def _get_communities(self) -> list[dict]:
        """Get graph communities (placeholder for Neo4j GDS integration)."""
        # In production, this would use Neo4j Graph Data Science library
        # for Leiden/Louvain community detection
        try:
            self.neo4j.connect()
            async with self.neo4j._driver.session() as session:
                result = await session.run("""
                    MATCH (n:KnowledgeNode)
                    WITH n.node_type as type, collect(n) as nodes
                    WHERE size(nodes) > 1
                    RETURN type as name,
                           size(nodes) as entity_count,
                           'Community based on node type' as description
                    LIMIT 20
                """)
                communities = []
                async for record in result:
                    communities.append({
                        "id": record["name"],
                        "name": record["name"],
                        "entity_count": record["entity_count"],
                        "description": record["description"],
                    })
                return communities
        except Exception:
            return []

    async def _get_community_entities(self, community_id: str) -> list[dict]:
        """Get entities in a community."""
        try:
            self.neo4j.connect()
            async with self.neo4j._driver.session() as session:
                result = await session.run("""
                    MATCH (n:KnowledgeNode {node_type: $community_id})
                    RETURN n.slug as slug, n.name as name, n.node_type as node_type
                    LIMIT 50
                """, community_id=community_id)
                entities = []
                async for record in result:
                    entities.append({
                        "slug": record["slug"],
                        "name": record["name"],
                        "node_type": record["node_type"],
                    })
                return entities
        except Exception:
            return []

    async def _get_documents_for_entities(
        self,
        entity_slugs: list[str],
    ) -> list[str]:
        """Get document IDs containing specific entities."""
        # This is a simplified version that would need the actual schema
        # In production, this could join through a entity-document mapping table
        try:
            self.neo4j.connect()
            async with self.neo4j._driver.session() as session:
                result = await session.run("""
                    MATCH (n:KnowledgeNode)-[:MENTIONED_IN]->(d:Document)
                    WHERE n.slug IN $slugs
                    RETURN DISTINCT d.id as doc_id
                    LIMIT 50
                """, slugs=entity_slugs)
                doc_ids = []
                async for record in result:
                    if record["doc_id"]:
                        doc_ids.append(str(record["doc_id"]))
                return doc_ids
        except Exception:
            return []


# Import LLM client for entity extraction
from app.services.llm.client import get_llm_client
