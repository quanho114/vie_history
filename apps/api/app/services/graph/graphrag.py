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


from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db_context

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

    async def _is_neo4j_active(self) -> bool:
        """Check if Neo4j is configured, enabled, and reachable."""
        from app.core.config import settings
        if not getattr(settings, "ENABLE_GRAPH", True):
            return False
        try:
            return await self.neo4j.check_connection()
        except Exception:
            return False

    async def local_search(
        self,
        query: str,
        entities: list[str] | None = None,
        depth: int = 2,
        top_k: int = 5,
        db: AsyncSession | None = None,
    ) -> GraphRAGResult:
        """
        Local GraphRAG search — entity-centric.

        1. Extract/find entities from query
        2. Get entity neighborhoods (multi-hop)
        3. Get documents containing these entities
        4. Synthesize with graph context (weighted by PageRank)
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
            from app.services.graph.graph_service import _slugify
            slug = _slugify(entity)
            neighborhood = await self._traverse_entity(
                slug,
                depth=depth,
                visited=visited,
                db=db,
            )
            all_entities.extend(neighborhood.get("entities", []))
            all_relationships.extend(neighborhood.get("relationships", []))

        # 3. Get documents containing these entities
        entity_slugs = [e.get("slug") or e.get("node_slug") for e in all_entities]
        entity_slugs = [s for s in entity_slugs if s]
        doc_ids = await self._get_documents_for_entities(entity_slugs, db=db)

        # 4. Score documents by graph relevance (with PageRank weighting)
        chunks = await self._get_graph_boosted_chunks(
            query=query,
            entity_slugs=entity_slugs,
            graph_entities=all_entities,
            graph_relationships=all_relationships,
            top_k=top_k,
            db=db,
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
        db: AsyncSession | None = None,
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
        communities = await self._get_communities(db=db)

        # 2. Score communities by relevance to query
        scored_communities = []
        for community in communities:
            community_entities = await self._get_community_entities(community["id"], db=db)

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
                [e.get("slug") for e in sc["entities"] if e.get("slug")],
                db=db
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
        db: AsyncSession | None = None,
    ) -> GraphRAGResult:
        """
        Hybrid GraphRAG: combine graph context with vector search.

        1. Extract entities from query
        2. Get graph context (entities, relationships)
        3. Run vector search
        4. Score by graph relevance (weighted by PageRank)
        5. Return enriched results
        """
        # Get graph context
        graph_context = await self._get_graph_context(query, db=db)

        # Run hybrid vector search
        try:
            chunks = await self.query_service.hybrid_search(
                query=query,
                top_k=top_k,
                filters=filters,
            )
        except Exception:
            chunks = []

        # Get PageRank scores for boosting
        pagerank_scores = {}
        try:
            from app.services.graph.graph_reasoner import GraphReasoner
            reasoner = GraphReasoner()
            if db is not None:
                pagerank_scores = await reasoner.get_pagerank(db)
            else:
                async with get_db_context() as local_db:
                    pagerank_scores = await reasoner.get_pagerank(local_db)
        except Exception as e:
            logger.warning("failed_to_get_pagerank_for_hybrid_boosting", error=str(e))

        # Score documents by graph relevance
        scored_chunks = self._score_by_graph_relevance(
            chunks=chunks,
            graph_context=graph_context,
            pagerank_scores=pagerank_scores,
        )

        return GraphRAGResult(
            entities=graph_context.get("entities", []),
            relationships=graph_context.get("relationships", []),
            document_ids=[c.get("document_id") for c in scored_chunks if c.get("document_id")],
            reasoning_chain=[
                f"Found {len(graph_context.get('entities', []))} related entities",
                f"Found {len(graph_context.get('relationships', []))} relationships",
                f"Retrieved {len(chunks)} document chunks",
                f"Scored by PageRank-weighted graph relevance",
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
        db: AsyncSession | None = None,
    ) -> dict[str, Any]:
        """Multi-hop entity traversal from Neo4j or NetworkX (fallback)."""
        if depth == 0 or entity_slug in visited:
            return {"entities": [], "relationships": []}

        visited.add(entity_slug)
        entities = []
        relationships = []

        neo4j_active = await self._is_neo4j_active()

        # Get current entity
        try:
            if neo4j_active:
                current = await self.neo4j.get_node_by_slug(entity_slug)
            else:
                from app.services.graph.graph_service import GraphService
                if db is not None:
                    current_node = await GraphService.get_node_by_slug(db, entity_slug)
                else:
                    async with get_db_context() as local_db:
                        current_node = await GraphService.get_node_by_slug(local_db, entity_slug)
                current = {
                    "slug": current_node.slug,
                    "name": current_node.name,
                    "node_type": current_node.node_type,
                    "description": current_node.description,
                    "wiki_page_id": current_node.wiki_page_id,
                    "event_id": current_node.event_id,
                } if current_node else None

            if current:
                entities.append(current)
        except Exception as e:
            logger.warning("graphrag_get_node_failed", slug=entity_slug, error=str(e))

        # Get neighbors
        try:
            if neo4j_active:
                neighbors_result = await self.neo4j.get_neighbors(entity_slug, depth=1)
            else:
                from app.services.graph.graph_reasoner import GraphReasoner
                reasoner = GraphReasoner()
                if db is not None:
                    neighbors_result = await reasoner.get_neighbors(db, entity_slug, depth=1)
                else:
                    async with get_db_context() as local_db:
                        neighbors_result = await reasoner.get_neighbors(local_db, entity_slug, depth=1)
            
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
                            neighbor_slug, depth - 1, visited, db=db
                        )
                        entities.extend(sub.get("entities", []))
                        relationships.extend(sub.get("relationships", []))
        except Exception as e:
            logger.warning("graphrag_get_neighbors_failed", slug=entity_slug, error=str(e))

        return {"entities": entities, "relationships": relationships}

    async def _get_graph_context(self, query: str, db: AsyncSession | None = None) -> dict[str, Any]:
        """Get graph context relevant to the query."""
        try:
            entities = await self._extract_entities(query)
            if not entities:
                return {"entities": [], "relationships": []}

            # Get neighbors for top entities
            all_entities = []
            all_relationships = []
            neo4j_active = await self._is_neo4j_active()

            for entity_name in entities[:5]:
                from app.services.graph.graph_service import _slugify
                slug = _slugify(entity_name)
                try:
                    if neo4j_active:
                        neighbors_result = await self.neo4j.get_neighbors(slug, depth=1)
                    else:
                        from app.services.graph.graph_reasoner import GraphReasoner
                        reasoner = GraphReasoner()
                        if db is not None:
                            neighbors_result = await reasoner.get_neighbors(db, slug, depth=1)
                        else:
                            async with get_db_context() as local_db:
                                neighbors_result = await reasoner.get_neighbors(local_db, slug, depth=1)
                    
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
        pagerank_scores: dict[str, float] | None = None,
    ) -> list[dict[str, Any]]:
        """Boost chunks that mention graph entities, weighted by PageRank/centrality."""
        entity_names = {}
        for e in graph_context.get("entities", []):
            name = e.get("name") or e.get("node_name")
            slug = e.get("slug") or e.get("node_slug")
            if name:
                entity_names[name.lower()] = slug

        relationship_types = {
            r.get("type", "").lower() or r.get("edge_type", "").lower()
            for r in graph_context.get("relationships", [])
        }

        pr_scores = pagerank_scores or {}

        scored = []
        for chunk in chunks:
            chunk = dict(chunk)  # Copy to avoid mutation
            content = chunk.get("content", "").lower()
            graph_boost = 0.0

            for name, slug in entity_names.items():
                if name and name in content:
                    pr_weight = pr_scores.get(slug, 0.0) if slug else 0.0
                    weight_boost = min(pr_weight * 10.0, 0.2)
                    graph_boost += 0.1 + weight_boost

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
        db: AsyncSession | None = None,
    ) -> list[dict[str, Any]]:
        """Get chunks boosted by graph relevance."""
        chunks = await self.vector_search.search(query, top_k=top_k * 2)

        graph_context = {
            "entities": graph_entities,
            "relationships": graph_relationships,
        }

        pagerank_scores = {}
        try:
            from app.services.graph.graph_reasoner import GraphReasoner
            reasoner = GraphReasoner()
            if db is not None:
                pagerank_scores = await reasoner.get_pagerank(db)
            else:
                async with get_db_context() as local_db:
                    pagerank_scores = await reasoner.get_pagerank(local_db)
        except Exception as e:
            logger.warning("failed_to_get_pagerank_for_boosted_chunks", error=str(e))

        scored = self._score_by_graph_relevance(chunks, graph_context, pagerank_scores)
        return scored[:top_k]

    async def _get_communities(self, db: AsyncSession | None = None) -> list[dict]:
        """Get graph communities (with NetworkX Louvain fallback if Neo4j is offline)."""
        neo4j_active = await self._is_neo4j_active()
        if neo4j_active:
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
            except Exception as e:
                logger.warning("neo4j_get_communities_failed_trying_fallback", error=str(e))

        try:
            from app.services.graph.graph_reasoner import GraphReasoner
            reasoner = GraphReasoner()
            if db is not None:
                g = await reasoner._get_cached_graph(db)
            else:
                async with get_db_context() as local_db:
                    g = await reasoner._get_cached_graph(local_db)

            if g.number_of_nodes() == 0:
                return []

            try:
                import networkx.algorithms.community as nx_comm
                communities_sets = nx_comm.louvain_communities(g.to_undirected(), weight='weight')
                communities = []
                for idx, c_set in enumerate(communities_sets):
                    if len(c_set) < 2:
                        continue
                    c_nodes = list(c_set)
                    center_node_id = max(c_nodes, key=lambda n: g.degree(n))
                    center_node_name = g.nodes[center_node_id].get("name", f"Nhóm {idx}")

                    communities.append({
                        "id": f"community_{idx}",
                        "name": f"Nhóm thực thể quanh {center_node_name}",
                        "entity_count": len(c_set),
                        "description": f"Cộng đồng NetworkX phát hiện xung quanh thực thể {center_node_name}",
                        "node_ids": list(c_set)
                    })
                return communities
            except Exception as ex:
                logger.warning("nx_louvain_failed_using_type_grouping", error=str(ex))
                type_groups = {}
                for nid, attrs in g.nodes(data=True):
                    ntype = attrs.get("node_type", "Concept")
                    if ntype not in type_groups:
                        type_groups[ntype] = []
                    type_groups[ntype].append(nid)

                communities = []
                for idx, (ntype, nodes) in enumerate(type_groups.items()):
                    if len(nodes) < 2:
                        continue
                    communities.append({
                        "id": ntype,
                        "name": f"Nhóm {ntype}",
                        "entity_count": len(nodes),
                        "description": f"Cộng đồng dựa trên loại thực thể {ntype}",
                        "node_ids": nodes
                    })
                return communities
        except Exception as e:
            logger.error("networkx_get_communities_failed", error=str(e))
            return []

    async def _get_community_entities(self, community_id: str, db: AsyncSession | None = None) -> list[dict]:
        """Get entities in a community."""
        neo4j_active = await self._is_neo4j_active()
        if neo4j_active and not community_id.startswith("community_"):
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
                pass

        try:
            from app.services.graph.graph_reasoner import GraphReasoner
            reasoner = GraphReasoner()
            if db is not None:
                g = await reasoner._get_cached_graph(db)
            else:
                async with get_db_context() as local_db:
                    g = await reasoner._get_cached_graph(local_db)

            entities = []
            if community_id.startswith("community_"):
                import networkx.algorithms.community as nx_comm
                try:
                    communities_sets = nx_comm.louvain_communities(g.to_undirected(), weight='weight')
                    idx = int(community_id.split("_")[1])
                    if idx < len(communities_sets):
                        c_set = communities_sets[idx]
                        for nid in c_set:
                            attrs = g.nodes[nid]
                            entities.append({
                                "slug": attrs.get("slug"),
                                "name": attrs.get("name"),
                                "node_type": attrs.get("node_type"),
                            })
                except Exception:
                    pass
            else:
                for nid, attrs in g.nodes(data=True):
                    if attrs.get("node_type") == community_id:
                        entities.append({
                            "slug": attrs.get("slug"),
                            "name": attrs.get("name"),
                            "node_type": attrs.get("node_type"),
                        })
            return entities
        except Exception:
            return []

    async def _get_documents_for_entities(
        self,
        entity_slugs: list[str],
        db: AsyncSession | None = None,
    ) -> list[str]:
        """Get document IDs containing specific entities."""
        neo4j_active = await self._is_neo4j_active()
        if neo4j_active:
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
                pass

        try:
            from sqlalchemy import select
            from app.models.graph import KnowledgeNode, KnowledgeEdge
            doc_ids = set()

            async def process_nodes(session):
                node_stmt = select(KnowledgeNode).where(KnowledgeNode.slug.in_(entity_slugs))
                res = await session.execute(node_stmt)
                nodes = res.scalars().all()
                node_ids = [n.id for n in nodes]
                if not node_ids:
                    return

                edge_stmt = select(KnowledgeEdge).where(
                    KnowledgeEdge.source_id.in_(node_ids),
                    KnowledgeEdge.edge_type == "MENTIONED_IN"
                )
                edge_res = await session.execute(edge_stmt)
                edges = edge_res.scalars().all()
                target_ids = [e.target_id for e in edges]
                if not target_ids:
                    return

                doc_stmt = select(KnowledgeNode).where(
                    KnowledgeNode.id.in_(target_ids),
                    KnowledgeNode.node_type == "Document"
                )
                doc_res = await session.execute(doc_stmt)
                doc_nodes = doc_res.scalars().all()
                for doc_node in doc_nodes:
                    doc_ids.add(doc_node.slug or doc_node.id)

            if db is not None:
                await process_nodes(db)
            else:
                async with get_db_context() as local_db:
                    await process_nodes(local_db)
            return list(doc_ids)
        except Exception as e:
            logger.warning("postgres_get_documents_for_entities_failed", error=str(e))
            return []


# Import LLM client for entity extraction
from app.services.llm.client import get_llm_client

