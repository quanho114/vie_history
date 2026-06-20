import pytest
from app.services.retrieval.query_expansion import QueryExpansionAgent

def test_historical_expansion():
    agent = QueryExpansionAgent()
    expanded = agent.expand("Quang Trung đánh quân Thanh")
    assert "Nguyễn Huệ" in expanded
    assert "Bắc Bình Vương" in expanded
