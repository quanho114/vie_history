"""Unit tests for Agent routing and supervisor node planning behavior."""

import pytest
from app.agents.agent_graph import supervisor_node


@pytest.mark.asyncio
async def test_supervisor_fast_routing():
    """Simple query should route directly to retrieval and bypass complex analysis nodes."""
    state = {
        "query": "Hồ Chí Minh sinh năm bao nhiêu?",
        "execution_mode": "agentic",
        "replanning_required": False,
        "agent_trace": [],
        "plan": [],
        "replanning_count": 0,
        "critic_feedback": None
    }
    
    result = await supervisor_node(state)
    
    # For a simple query, it should plan retrieval_node and bypass world_model_node or graph_node
    assert "retrieval_node" in result["plan"]
    assert "graph_node" not in result["plan"]
    assert "world_model_node" not in result["plan"]
