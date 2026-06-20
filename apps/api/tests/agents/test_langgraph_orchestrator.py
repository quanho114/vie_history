import pytest
from app.agents.agent_state import AgentState
from app.agents.langgraph_orchestrator import LangGraphOrchestrator

@pytest.mark.asyncio
async def test_langgraph_agent_flow():
    orchestrator = LangGraphOrchestrator()
    result = await orchestrator.run("Nhà Trần thắng quân Nguyên Mông nhờ chiến thuật gì?")
    
    assert result["final_answer"] is not None
    assert len(result["retrieved_docs"]) > 0
    assert "factual" in result["intent"]
