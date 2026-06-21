import pytest
from app.services.agent.planner import HistoricalPlanner

def test_tool_registry_filtering():
    planner = HistoricalPlanner()
    # If the planner generates a raw plan containing invalid or hallucinated tools:
    raw_plan = {
        "tasks": [
            {"tool": "graph", "reason": "Query relation"},
            {"tool": "internet_search", "reason": "Hallucinated tool"}
        ]
    }
    validated = planner.validate_plan(raw_plan)
    
    tools = [t["tool"] for t in validated["tasks"]]
    assert "graph" in tools
    assert "internet_search" not in tools
    assert len(tools) == 1
