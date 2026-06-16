"""Unit tests for the Brain Router & Graph Reasoning integration."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.brain.brain_router import BrainRouter, _slugify_basic
from app.services.graph.graph_reasoner import GraphReasoner


def test_slugify_basic() -> None:
    """Verify raw Vietnamese text is correctly slugified to clean URL-friendly ASCII."""
    assert _slugify_basic("Chiến dịch Điện Biên Phủ") == "chien-dich-dien-bien-phu"
    assert _slugify_basic("  Bác Hồ   ") == "bac-ho"
    assert _slugify_basic("Hiệp định Genève 1954") == "hiep-dinh-geneve-1954"
    assert _slugify_basic("Đại tướng Võ Nguyên Giáp!") == "dai-tuong-vo-nguyen-giap"


@pytest.mark.asyncio
async def test_brain_router_empty_routing() -> None:
    """Verify brain router returns empty results when no routing hints are set."""
    router = BrainRouter()
    db = AsyncMock()

    result = await router.route(
        db=db,
        query="Không có gì đặc biệt",
        intent="factual",
        routing_hints={},
        entities=[],
    )

    assert result.intent == "factual"
    assert result.wiki_results == []
    assert result.timeline_results == []
    assert result.graph_results == {"nodes": [], "edges": [], "paths": []}


@pytest.mark.asyncio
async def test_brain_router_wiki_search_triggered() -> None:
    """Verify wiki search is called when use_wiki is active."""
    router = BrainRouter()
    db = AsyncMock()

    # Mock the return value of db.execute for WikiPage lookup
    mock_execute_result = MagicMock()
    mock_row_1 = MagicMock()
    mock_row_1.slug = "dien-bien-phu"
    mock_row_1.title = "Chiến dịch Điện Biên Phủ"
    mock_row_1.summary = "Trận chiến lẫy lừng năm châu"
    mock_row_1.period = "1945-1954"
    mock_row_1.event_type = "military"
    mock_row_1.content = {"background": "Thực dân Pháp xây dựng tập đoàn cứ điểm"}
    mock_row_1.start_year = 1954
    mock_row_1.end_year = 1954

    mock_execute_result.fetchall.return_value = [mock_row_1]
    db.execute.return_value = mock_execute_result

    result = await router.route(
        db=db,
        query="Điện Biên Phủ",
        intent="factual",
        routing_hints={"use_wiki": True},
        entities=["Điện Biên Phủ"],
    )

    assert len(result.wiki_results) == 1
    assert result.wiki_results[0]["slug"] == "dien-bien-phu"
    assert result.wiki_results[0]["title"] == "Chiến dịch Điện Biên Phủ"
    assert result.wiki_results[0]["start_year"] == 1954


@pytest.mark.asyncio
async def test_brain_router_timeline_search_triggered() -> None:
    """Verify timeline search is called when use_timeline is active."""
    router = BrainRouter()
    db = AsyncMock()

    # Mock the return value of db.execute for HistoricalEvent lookup
    mock_execute_result = MagicMock()
    mock_row_1 = MagicMock()
    mock_row_1.slug = "hiep-dinh-geneve"
    mock_row_1.event_name = "Hiệp định Genève"
    mock_row_1.start_year = 1954
    mock_row_1.end_year = 1954
    mock_row_1.period = "1945-1954"
    mock_row_1.summary = "Ký kết hiệp định đình chiến tại Đông Dương"
    mock_row_1.event_type = "diplomatic"
    mock_row_1.importance_level = 5

    mock_execute_result.fetchall.return_value = [mock_row_1]
    db.execute.return_value = mock_execute_result

    result = await router.route(
        db=db,
        query="Hiệp định Genève năm 1954",
        intent="timeline",
        routing_hints={"use_timeline": True},
        entities=["Hiệp định Genève"],
    )

    assert len(result.timeline_results) == 1
    assert result.timeline_results[0]["slug"] == "hiep-dinh-geneve"
    assert result.timeline_results[0]["event_name"] == "Hiệp định Genève"
    assert result.timeline_results[0]["start_year"] == 1954


@pytest.mark.asyncio
async def test_brain_router_graph_search_cause_effect_path() -> None:
    """Verify graph search performs causal pathfinding and neighborhood search."""
    router = BrainRouter()
    db = AsyncMock()

    mock_reasoner = MagicMock(spec=GraphReasoner)
    
    # Mock find_path
    mock_reasoner.find_path = AsyncMock(return_value=[
        {"node_id": "1", "node_slug": "dien-bien-phu", "node_name": "Chiến dịch Điện Biên Phủ", "node_type": "Event", "edge_type": None},
        {"node_id": "2", "node_slug": "hiep-dinh-geneve", "node_name": "Hiệp định Genève", "node_type": "Agreement", "edge_type": "LED_TO"}
    ])

    # Mock get_neighbors for both entities
    mock_reasoner.get_neighbors = AsyncMock(side_effect=[
        {
            "node": {"node_id": "1", "slug": "dien-bien-phu", "name": "Chiến dịch Điện Biên Phủ", "node_type": "Event", "description": "Lẫy lừng"},
            "neighbors": [
                {"node_id": "3", "node_slug": "vo-nguyen-giap", "node_name": "Võ Nguyên Giáp", "node_type": "Person", "edge_type": "LED_BY", "direction": "outgoing", "depth": 1}
            ]
        },
        {
            "node": {"node_id": "2", "slug": "hiep-dinh-geneve", "name": "Hiệp định Genève", "node_type": "Agreement", "description": "Đình chiến"},
            "neighbors": []
        }
    ])

    with patch("app.services.brain.brain_router.GraphReasoner", return_value=mock_reasoner):
        result = await router.route(
            db=db,
            query="Nguyên nhân dẫn đến Hiệp định Genève từ Điện Biên Phủ",
            intent="cause_effect",
            routing_hints={"use_graph": True},
            entities=["Chiến dịch Điện Biên Phủ", "Hiệp định Genève"],
        )

        # Check path finding was invoked
        mock_reasoner.find_path.assert_called_once_with(
            db,
            source_slug="chien-dich-dien-bien-phu",
            target_slug="hiep-dinh-geneve",
        )

        # Check neighborhood expansion was invoked for center nodes
        assert mock_reasoner.get_neighbors.call_count == 2

        # Check returned nodes and edges de-duplication
        graph = result.graph_results
        assert len(graph["paths"]) == 1
        assert len(graph["paths"][0]) == 2
        assert any(n["slug"] == "dien-bien-phu" for n in graph["nodes"])
        assert any(n["slug"] == "hiep-dinh-geneve" for n in graph["nodes"])
        assert any(n["slug"] == "vo-nguyen-giap" for n in graph["nodes"])
        assert len(graph["edges"]) == 1
        assert graph["edges"][0]["edge_type"] == "LED_BY"
