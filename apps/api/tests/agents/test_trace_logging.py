"""Unit tests for agent trace telemetry parameters (duration, reasoning logs)."""

import pytest
from unittest.mock import AsyncMock
from app.agents.agent_graph import retrieval_node


@pytest.mark.asyncio
async def test_trace_contains_action_reason(monkeypatch):
    """Verify that retrieval_node trace output returns duration_ms and action_reason fields."""
    state = {
        "query": "Chiến dịch Điện Biên Phủ",
        "retrieval_queries": ["Chiến dịch Điện Biên Phủ"],
        "agent_trace": [],
        "current_step": 0
    }
    
    # Mock QueryService.hybrid_search to avoid network/database dependency during tests
    from app.services.retrieval.query_service import QueryService
    monkeypatch.setattr(QueryService, "hybrid_search", AsyncMock(return_value=[
        {"id": "doc-1", "content": "Nội dung Điện Biên Phủ", "score": 0.9}
    ]))
    
    result = await retrieval_node(state)
    trace = result.get("agent_trace", [])
    
    assert len(trace) > 0
    assert "duration_ms" in trace[0]
    assert "action_reason" in trace[0]
    assert trace[0]["agent"] == "Retrieval Agent"
    assert trace[0]["status"] == "success"
