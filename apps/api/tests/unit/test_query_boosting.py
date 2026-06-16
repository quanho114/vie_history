"""Unit tests for query metadata boosting in QueryService."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.retrieval.query_service import QueryService

@pytest.mark.asyncio
async def test_metadata_aware_boosting(monkeypatch) -> None:
    # Mock search dependencies
    mock_embedder = MagicMock()
    mock_vector = MagicMock()
    mock_fusion = MagicMock()
    
    # Mock fusion output: two items, one with dynasty Nguyễn and one without
    mock_fusion.fuse.return_value = [
        {
            "id": "1",
            "document_id": "doc1",
            "document_title": "Doc 1",
            "content": "Content about Nguyễn dynasty",
            "rrf_score": 0.5,
            "score": 0.5,
            "dynasty": "Nguyễn"
        },
        {
            "id": "2",
            "document_id": "doc2",
            "document_title": "Doc 2",
            "content": "Content about Lý dynasty",
            "rrf_score": 0.8,
            "score": 0.8,
            "dynasty": "Lý"
        }
    ]

    service = QueryService(
        embedder=mock_embedder,
        vector_search=mock_vector,
        candidate_size=10,
        final_top_k=5,
        use_hyde=False
    )
    service.fusion = mock_fusion
    
    # Mock first stage to return empty lists since we mock fusion
    async def mock_first_stage(*args, **kwargs):
        return [], []
    monkeypatch.setattr(service, "_first_stage", mock_first_stage)
    
    # Search for something containing "Nguyễn"
    results = await service.hybrid_search(
        query="Kinh đô triều Nguyễn",
        top_k=2,
        skip_rerank=True
    )
    
    # Result "1" (Nguyễn) originally had score 0.5, with 1.2x boost it should be 0.6
    # Result "2" (Lý) originally had score 0.8, no boost
    # Thus, result 2 should still be first (0.8 vs 0.6)
    assert results[0]["chunk_id"] == "2"
    assert results[0]["score"] == 0.8
    assert results[1]["chunk_id"] == "1"
    assert abs(results[1]["score"] - 0.6) < 1e-5
