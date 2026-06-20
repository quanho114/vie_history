import pytest
from app.services.agent.tool_selector import ToolSelector

def test_tool_selector():
    selector = ToolSelector()
    tools = selector.select_tools("Quan hệ gia phả giữa Gia Long và Quang Trung?")
    assert "neo4j" in tools
