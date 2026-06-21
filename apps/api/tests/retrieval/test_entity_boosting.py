"""Unit tests for entity boosting and alias-aware retrieval boosting."""

import pytest
from app.services.retrieval.query_service import QueryService


@pytest.mark.asyncio
async def test_entity_boosting_alias():
    """Verify that chunks mentioning query entities or their canonical aliases are boosted appropriately."""
    service = QueryService()
    
    # Mock search output chunks
    chunks = [
        {
            "id": "1",
            "content": "Nguyễn Huệ tiến ra Thăng Long đại phá quân Thanh.",
            "rerank_score": 0.8
        },
        {
            "id": "2",
            "content": "Vua Quang Trung lãnh đạo phong trào Tây Sơn.",
            "rerank_score": 0.7
        },
        {
            "id": "3",
            "content": "Tài liệu khác không liên quan.",
            "rerank_score": 0.9
        }
    ]
    
    # We query about Quang Trung
    query = "Vua Quang Trung dẹp quân Thanh"
    
    # Check if Quang Trung and Nguyễn Huệ chunks receive boosts
    boosted = service._apply_entity_boosting(query, chunks)
    
    # Nguyễn Huệ (chunk 1) should be boosted because Nguyễn Huệ is an alias of Quang Trung
    # Rerank score of Nguyễn Huệ (0.8) boosted by 1.25x = 1.0, making it top result
    assert boosted[0]["id"] == "1"
    assert boosted[0]["rerank_score"] == pytest.approx(1.0)
    
    # Quang Trung (chunk 2) should also be boosted because Quang Trung matches "quang trung" query
    # Rerank score of Quang Trung (0.7) boosted by 1.25x = 0.875
    assert boosted[2]["id"] == "2"
    assert boosted[2]["rerank_score"] == pytest.approx(0.875)
