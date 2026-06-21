"""Unit tests for GraphRAGService — covers Local/Global/Hybrid modes,
NetworkX fallbacks, and PageRank-weighted retrieval boosting."""

from __future__ import annotations

import pytest
import networkx as nx
from unittest.mock import AsyncMock, MagicMock

from app.services.graph.graphrag import GraphRAGService, GraphRAGResult
from tests.unit.test_graph_reasoner import MockNode, _build_simple_graph


@pytest.mark.asyncio
async def test_graphrag_local_search_fallback(monkeypatch):
    """Test local search with fallback to local NetworkX graph traversal."""
    # 1. Mock dependency services
    vector_mock = AsyncMock()
    vector_mock.search = AsyncMock(return_value=[
        {"content": "Node B is connected to Node A", "document_id": "doc-1", "score": 0.8}
    ])
    
    service = GraphRAGService(
        neo4j_service=MagicMock(),
        vector_search=vector_mock,
        query_service=MagicMock()
    )

    # Mock _is_neo4j_active as False (forcing NetworkX fallback)
    monkeypatch.setattr(service, "_is_neo4j_active", AsyncMock(return_value=False))
    
    # Mock entity extraction
    monkeypatch.setattr(service, "_extract_entities", AsyncMock(return_value=["Node B"]))

    # Mock GraphReasoner neighbors call
    from app.services.graph.graph_reasoner import GraphReasoner
    reasoner_mock = MagicMock()
    reasoner_mock.get_neighbors = AsyncMock(return_value={
        "node": {"node_slug": "node-b", "node_name": "Node B", "node_type": "Event"},
        "neighbors": [
            {"node_slug": "node-a", "node_name": "Node A", "edge_type": "LED_TO"},
            {"node_slug": "node-c", "node_name": "Node C", "edge_type": "CAUSED_BY"}
        ]
    })
    
    # PageRank mock returning scores
    reasoner_mock.get_pagerank = AsyncMock(return_value={
        "node-a": 0.2,
        "node-b": 0.5,
        "node-c": 0.3
    })
    
    monkeypatch.setattr(GraphReasoner, "get_neighbors", reasoner_mock.get_neighbors)
    monkeypatch.setattr(GraphReasoner, "get_pagerank", reasoner_mock.get_pagerank)

    # Mock database session
    db_mock = AsyncMock()

    # Mock postgres fallback for documents containing entities
    monkeypatch.setattr(service, "_get_documents_for_entities", AsyncMock(return_value=["doc-1"]))

    # Run local search
    result = await service.local_search("Câu hỏi về Node B", db=db_mock)

    assert len(result.entities) > 0
    assert result.entities[0].get("node_slug") in ["node-a", "node-c"]
    assert len(result.chunks) == 1
    assert "doc-1" in result.document_ids
    assert "local_db" not in result.reasoning_chain


@pytest.mark.asyncio
async def test_graphrag_global_search_louvain(monkeypatch):
    """Test global search with fallback to NetworkX Louvain community detection."""
    service = GraphRAGService(
        neo4j_service=MagicMock(),
        vector_search=AsyncMock(),
        query_service=AsyncMock()
    )

    monkeypatch.setattr(service, "_is_neo4j_active", AsyncMock(return_value=False))

    # Mock cached NetworkX graph for Louvain
    graph = _build_simple_graph()
    from app.services.graph.graph_reasoner import GraphReasoner
    monkeypatch.setattr(GraphReasoner, "_get_cached_graph", AsyncMock(return_value=graph))

    # Mock postgres document lookup
    monkeypatch.setattr(service, "_get_documents_for_entities", AsyncMock(return_value=["doc-1", "doc-2"]))

    # Run global search
    result = await service.global_search("Tìm kiếm tổng quan về Node B")

    assert result.community_context != ""
    assert len(result.document_ids) > 0
    assert "Louvain" in result.reasoning_chain[3] or "communities" in result.reasoning_chain[0]


@pytest.mark.asyncio
async def test_graphrag_hybrid_search(monkeypatch):
    """Test hybrid search combining vector search chunks and PageRank boosting."""
    query_mock = AsyncMock()
    query_mock.hybrid_search = AsyncMock(return_value=[
        {"content": "This mentions Node B details", "document_id": "doc-1", "score": 0.6, "rerank_score": 0.2},
        {"content": "This is completely irrelevant", "document_id": "doc-2", "score": 0.4, "rerank_score": 0.1}
    ])

    service = GraphRAGService(
        neo4j_service=MagicMock(),
        vector_search=AsyncMock(),
        query_service=query_mock
    )

    monkeypatch.setattr(service, "_is_neo4j_active", AsyncMock(return_value=False))

    # Mock extract entities & graph context
    monkeypatch.setattr(service, "_extract_entities", AsyncMock(return_value=["Node B"]))
    monkeypatch.setattr(service, "_get_graph_context", AsyncMock(return_value={
        "entities": [{"name": "Node B", "slug": "node-b"}],
        "relationships": [{"type": "LED_TO"}]
    }))

    # Mock PageRank scores
    from app.services.graph.graph_reasoner import GraphReasoner
    reasoner_mock = MagicMock()
    reasoner_mock.get_pagerank = AsyncMock(return_value={"node-b": 0.8})
    monkeypatch.setattr(GraphReasoner, "get_pagerank", reasoner_mock.get_pagerank)

    # Run hybrid search
    result = await service.hybrid_search("Query about Node B details")

    assert len(result.chunks) == 2
    # doc-1 mentions "Node B" which is matched, so it should get a PageRank-scaled graph boost
    assert result.chunks[0]["document_id"] == "doc-1"
    assert result.chunks[0]["graph_relevance_score"] > 0
    # doc-1 score should be boosted and be higher than doc-2
    assert result.chunks[0]["combined_score"] > result.chunks[1]["combined_score"]
