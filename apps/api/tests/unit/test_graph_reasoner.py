"""Unit tests for GraphReasoner — covers undirected-fallback path finding and
edge-direction annotation introduced in the enhancements phase."""

from __future__ import annotations

import pytest

# ---------------------------------------------------------------------------
# Helpers — build a tiny in-memory NetworkX graph without hitting the DB
# ---------------------------------------------------------------------------

import networkx as nx
from unittest.mock import AsyncMock, MagicMock

from app.services.graph.graph_reasoner import GraphReasoner


def _make_mock_db():
    return AsyncMock()


def _build_simple_graph() -> nx.DiGraph:
    """
    A → B (LED_TO)
    B → C (CAUSED_BY)
    """
    g: nx.DiGraph = nx.DiGraph()
    g.add_node("id-a", slug="node-a", name="Node A", node_type="Event", description="")
    g.add_node("id-b", slug="node-b", name="Node B", node_type="Event", description="")
    g.add_node("id-c", slug="node-c", name="Node C", node_type="Event", description="")

    g.add_edge("id-a", "id-b", id="e1", edge_type="LED_TO", weight=1.0, description="")
    g.add_edge("id-b", "id-c", id="e2", edge_type="CAUSED_BY", weight=1.0, description="")

    g.graph["slug_to_id"] = {"node-a": "id-a", "node-b": "id-b", "node-c": "id-c"}
    g.graph["id_to_node"] = {}
    return g


# ---------------------------------------------------------------------------
# Test: directed path (happy path)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_find_path_directed_happy_path(monkeypatch):
    """find_path should return the directed path A → B → C."""
    reasoner = GraphReasoner()
    graph = _build_simple_graph()
    monkeypatch.setattr(reasoner, "_get_cached_graph", AsyncMock(return_value=graph))

    steps = await reasoner.find_path(_make_mock_db(), "node-a", "node-c")

    assert len(steps) == 3
    slugs = [s["node_slug"] for s in steps]
    assert slugs == ["node-a", "node-b", "node-c"]
    # Edge types should follow directed path
    assert steps[1]["edge_type"] == "LED_TO"
    assert steps[2]["edge_type"] == "CAUSED_BY"


# ---------------------------------------------------------------------------
# Test: undirected fallback (reversed direction)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_find_path_undirected_fallback(monkeypatch):
    """
    When querying C → A (no directed path), find_path should fall back to the
    undirected graph and annotate reversed edges with '(ngược lại)'.
    """
    reasoner = GraphReasoner()
    graph = _build_simple_graph()
    monkeypatch.setattr(reasoner, "_get_cached_graph", AsyncMock(return_value=graph))

    steps = await reasoner.find_path(_make_mock_db(), "node-c", "node-a")

    # Should still return a path (C → B → A via undirected)
    assert len(steps) == 3
    slugs = [s["node_slug"] for s in steps]
    assert slugs == ["node-c", "node-b", "node-a"]

    # Edges are traversed in reverse — should be annotated
    for step in steps[1:]:
        assert "(ngược lại)" in (step["edge_type"] or "")


# ---------------------------------------------------------------------------
# Test: no path at all
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_find_path_no_path_raises(monkeypatch):
    """find_path should raise ValueError when no path exists in either direction."""
    reasoner = GraphReasoner()
    graph = _build_simple_graph()
    # Add an isolated node
    graph.add_node("id-d", slug="node-d", name="Node D", node_type="Event", description="")
    graph.graph["slug_to_id"]["node-d"] = "id-d"

    monkeypatch.setattr(reasoner, "_get_cached_graph", AsyncMock(return_value=graph))

    with pytest.raises(ValueError, match="No path"):
        await reasoner.find_path(_make_mock_db(), "node-a", "node-d")


# ---------------------------------------------------------------------------
# Test: unknown slug raises ValueError
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_find_path_unknown_slug_raises(monkeypatch):
    reasoner = GraphReasoner()
    graph = _build_simple_graph()
    monkeypatch.setattr(reasoner, "_get_cached_graph", AsyncMock(return_value=graph))

    with pytest.raises(ValueError, match="not found"):
        await reasoner.find_path(_make_mock_db(), "node-a", "does-not-exist")


# ---------------------------------------------------------------------------
# Test: parse_llm_json handles conversational prefixes
# ---------------------------------------------------------------------------

def test_parse_llm_json_with_conversational_prefix():
    """parse_llm_json should extract JSON even when LLM adds text before it."""
    from app.services.llm.json_parser import parse_llm_json

    raw = "Dưới đây là kết quả trích xuất:\n\n[{\"event_name\": \"Điện Biên Phủ\"}]"
    result = parse_llm_json(raw)
    assert isinstance(result, list)
    assert result[0]["event_name"] == "Điện Biên Phủ"


def test_parse_llm_json_with_markdown_fences():
    """parse_llm_json should handle ```json fenced blocks."""
    from app.services.llm.json_parser import parse_llm_json

    raw = "```json\n{\"nodes\": [], \"edges\": []}\n```"
    result = parse_llm_json(raw)
    assert result == {"nodes": [], "edges": []}


def test_parse_llm_json_raises_on_no_json():
    """parse_llm_json should raise ValueError when there is no JSON at all."""
    from app.services.llm.json_parser import parse_llm_json
    import pytest

    with pytest.raises(ValueError, match="No JSON found"):
        parse_llm_json("Xin lỗi, tôi không thể trả lời câu hỏi này.")
