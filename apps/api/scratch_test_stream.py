import asyncio
from app.agents.agent_graph import create_agent_graph

async def test():
    graph = create_agent_graph()
    initial_state = {
        "query": "Chiến dịch Hồ Chí Minh",
        "plan": [],
        "execution_mode": "fast",
        "retrieved_chunks": [],
        "timeline_events": [],
        "citations": [],
        "agent_trace": [],
        "replanning_required": False,
        "replanning_count": 0,
        "answer": None,
    }
    
    # Try different stream modes
    async for chunk in graph.astream(initial_state, stream_mode="debug"):
        print(chunk)

asyncio.run(test())
