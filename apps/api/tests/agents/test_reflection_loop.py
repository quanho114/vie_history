import pytest
from app.agents.langgraph_orchestrator import LangGraphOrchestrator

@pytest.mark.asyncio
async def test_critic_reflection_routing():
    orchestrator = LangGraphOrchestrator()
    # Complex prompt triggering reflection
    result = await orchestrator.run("Tại sao triều Hồ sụp đổ?")
    assert result["retry_count"] >= 1
