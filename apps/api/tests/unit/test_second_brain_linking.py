"""Tests for second-brain linking after wiki approval."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.wiki import WikiPage
from app.services.graph.graph_service import GraphService
from app.services.timeline.timeline_service import TimelineService
from app.services.wiki.wiki_pipeline import WikiPipeline


def _wiki_page() -> WikiPage:
    return WikiPage(
        id="wiki-1",
        slug="chien-dich-dien-bien-phu",
        title="Chiến dịch Điện Biên Phủ",
        summary="Trận đánh quyết định năm 1954.",
        content={
            "causes": ["Pháp xây dựng tập đoàn cứ điểm Điện Biên Phủ"],
            "results": ["Dẫn tới Hiệp định Genève"],
            "people": ["Võ Nguyên Giáp"],
            "timeline": [
                {
                    "title": "Chiến dịch Điện Biên Phủ",
                    "year": 1954,
                    "summary": "Trận đánh từ tháng 3 đến tháng 5 năm 1954.",
                }
            ],
        },
        status="draft",
        version=1,
        event_type="battle",
        period="khang_chien_chong_phap",
        start_year=1954,
        end_year=1954,
        source_document_ids=["doc-1"],
    )


@pytest.mark.asyncio
async def test_timeline_extracts_events_from_wiki_page_without_llm(monkeypatch) -> None:
    page = _wiki_page()
    db = AsyncMock()
    execute_result = MagicMock()
    execute_result.scalar_one_or_none.return_value = page
    db.execute.return_value = execute_result

    event = MagicMock()
    event.id = "event-1"
    event.slug = page.slug

    service = TimelineService()
    upsert = AsyncMock(return_value=event)
    monkeypatch.setattr(service, "_upsert_event", upsert)

    events = await service.extract_events_from_wiki_page(db, page.id)

    assert events == [event]
    payload = upsert.call_args.args[1]
    assert payload["wiki_page_id"] == page.id
    assert payload["slug"] == page.slug
    assert payload["start_year"] == 1954
    assert payload["source_document_ids"] == ["doc-1"]


@pytest.mark.asyncio
async def test_graph_extraction_falls_back_to_wiki_node_when_llm_fails(monkeypatch) -> None:
    page = _wiki_page()
    db = AsyncMock()

    page_result = MagicMock()
    page_result.scalar_one_or_none.return_value = page
    event_result = MagicMock()
    event_result.scalar_one_or_none.return_value = None
    db.execute.side_effect = [page_result, event_result]

    llm = MagicMock()
    llm.generate = AsyncMock(side_effect=RuntimeError("missing provider"))
    monkeypatch.setattr("app.services.graph.graph_service.get_llm_client", lambda: llm)

    node = MagicMock()
    node.id = "node-1"
    node.slug = page.slug

    service = GraphService()
    upsert_node = AsyncMock(return_value=node)
    monkeypatch.setattr(service, "_upsert_node", upsert_node)

    nodes, edges = await service.extract_graph_from_wiki_page(db, page.id)

    assert nodes == [node]
    assert edges == []
    payload = upsert_node.call_args.args[1]
    assert payload["slug"] == page.slug
    assert payload["wiki_page_id"] == page.id


@pytest.mark.asyncio
async def test_wiki_pipeline_links_timeline_and_graph(monkeypatch) -> None:
    page = _wiki_page()
    db = AsyncMock()

    timeline_service = MagicMock()
    timeline_service.extract_events_from_wiki_page = AsyncMock(return_value=[MagicMock()])
    graph_service = MagicMock()
    graph_service.extract_graph_from_wiki_page = AsyncMock(return_value=([MagicMock(), MagicMock()], [MagicMock()]))

    monkeypatch.setattr(
        "app.services.timeline.timeline_service.TimelineService",
        lambda: timeline_service,
    )
    monkeypatch.setattr(
        "app.services.graph.graph_service.GraphService",
        lambda: graph_service,
    )

    result = await WikiPipeline()._link_second_brain_stores(db, page)

    assert result == {"timeline_events": 1, "graph_nodes": 2, "graph_edges": 1}
    timeline_service.extract_events_from_wiki_page.assert_awaited_once_with(db, wiki_page_id=page.id)
    graph_service.extract_graph_from_wiki_page.assert_awaited_once_with(db, wiki_page_id=page.id)
