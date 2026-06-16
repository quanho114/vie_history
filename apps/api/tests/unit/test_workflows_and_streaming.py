"""Unit tests for the 5 custom workflows and AgentOrchestrator streaming."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.agent.workflows.factual import FactualWorkflow
from app.services.agent.workflows.timeline import TimelineWorkflow
from app.services.agent.workflows.compare import CompareWorkflow
from app.services.agent.workflows.summary import SummaryWorkflow
from app.services.agent.workflows.source_audit import SourceAuditWorkflow
from app.agents.orchestrator import AgentOrchestrator


@pytest.mark.asyncio
async def test_factual_workflow_limits_and_prompts() -> None:
    workflow = FactualWorkflow()
    chunks = [{"content": f"Chunk {i}", "document_title": f"Doc {i}"} for i in range(12)]
    
    # Verify prepare_data limits to 8
    prepared = await workflow.prepare_data("query", chunks)
    assert len(prepared) == 8

    # Verify prompts
    system, user = workflow.get_prompts("Ai là tổng tư lệnh chiến dịch Điện Biên Phủ?", prepared)
    assert "HistoriAI" in system
    assert "Ai là tổng tư lệnh" in user
    assert "[S1]" in user


@pytest.mark.asyncio
async def test_timeline_workflow_chronological_sorting() -> None:
    workflow = TimelineWorkflow()
    chunks = [
        {"content": "Sự kiện xảy ra năm 1975 giải phóng.", "document_title": "Chiến dịch 1975"},
        {"content": "Hiệp định Genève ký năm 1954 chia cắt.", "document_title": "Hiệp định 1954"},
        {"content": "Cách mạng tháng 8 năm 1945 thành công.", "document_title": "Cách mạng 1945"},
        {"content": "Sự kiện không rõ năm rõ ràng.", "document_title": "Tài liệu không rõ năm"},
    ]
    
    prepared = await workflow.prepare_data("query", chunks)
    
    # Verified chronological sorting: 1945 -> 1954 -> 1975 -> 9999
    assert "1945" in prepared[0]["content"]
    assert "1954" in prepared[1]["content"]
    assert "1975" in prepared[2]["content"]
    assert "không rõ năm" in prepared[3]["content"]

    system, user = workflow.get_prompts("Niên biểu sự kiện", prepared)
    assert "niên biểu/tiến trình lịch sử" in system
    assert "[S1]" in user


@pytest.mark.asyncio
async def test_compare_workflow_labels_subjects() -> None:
    workflow = CompareWorkflow()
    chunks = [
        {"content": "Hiệp định Genève năm 1954 quy định vĩ tuyến 17.", "document_title": "Hiệp định Genève"},
        {"content": "Hiệp định Paris năm 1973 ký kết lập lại hòa bình.", "document_title": "Hiệp định Paris"},
    ]
    
    # Parse Genève and Paris from query
    prepared = await workflow.prepare_data("So sánh Hiệp định Genève và Hiệp định Paris", chunks)
    
    # Verification that subjects are labeled
    assert "subject_label" in prepared[0]
    assert "subject_label" in prepared[1]

    system, user = workflow.get_prompts("So sánh Hiệp định Genève và Hiệp định Paris", prepared)
    assert "so sánh đối chiếu" in system
    assert "[S1]" in user


@pytest.mark.asyncio
async def test_summary_workflow() -> None:
    workflow = SummaryWorkflow()
    chunks = [{"content": f"Chunk {i}"} for i in range(15)]
    
    prepared = await workflow.prepare_data("Tóm tắt", chunks)
    assert len(prepared) == 12  # Limits to 12

    system, user = workflow.get_prompts("Tóm tắt chiến dịch", prepared)
    assert "tóm tắt phân lớp" in system
    assert "[S1]" in user


@pytest.mark.asyncio
async def test_source_audit_workflow_grouping() -> None:
    workflow = SourceAuditWorkflow()
    chunks = [
        {"content": "Chunk A1", "document_id": "doc_a", "document_title": "Doc A", "score": 0.9},
        {"content": "Chunk B1", "document_id": "doc_b", "document_title": "Doc B", "score": 0.8},
        {"content": "Chunk A2", "document_id": "doc_a", "document_title": "Doc A", "score": 0.9},
    ]
    
    prepared = await workflow.prepare_data("Nguồn tư liệu", chunks)
    
    # Doc A has 2 chunks, Doc B has 1. Doc A should be first and have high doc_rank
    assert prepared[0]["document_id"] == "doc_a"
    assert prepared[1]["document_id"] == "doc_a"
    assert prepared[2]["document_id"] == "doc_b"
    assert prepared[0]["doc_rank"] == 1
    assert prepared[2]["doc_rank"] == 2

    system, user = workflow.get_prompts("Nguồn tư liệu Điện Biên Phủ", prepared)
    assert "kiểm định nguồn tài liệu" in system
    assert "[S1]" in user


@pytest.mark.asyncio
async def test_orchestrator_answer_stream_generator() -> None:
    orchestrator = AgentOrchestrator()
    
    async def mock_stream_graph(initial_state, thread_id):
        yield {"supervisor_node": {"execution_mode": "factual", "agent_trace": [{"agent": "Supervisor", "action": "Classifying", "status": "success"}]}}
        yield {"retrieval_node": {"retrieved_chunks": [{"content": "Evidence chunk 1 [S1]", "document_title": "Doc 1"}], "agent_trace": [{"agent": "Retrieval", "action": "Retrieving", "status": "success"}]}}
        yield {"critic_node": {"critic_feedback": "Looks good", "agent_trace": [{"agent": "Critic", "action": "Verifying", "status": "success"}]}}
        yield {"reasoning_node": {"answer": "This is a mock answer [S1].", "citations": [{"document_title": "Doc 1"}], "agent_trace": [{"agent": "Reasoning", "action": "Generating", "status": "success"}]}}

    orchestrator._stream_agent_graph = mock_stream_graph
    
    db_mock = AsyncMock()
    
    # Iterate answer_stream
    events = []
    async for event in orchestrator.answer_stream("Test query", db=db_mock, mode="factual"):
        events.append(event)
        
    # Check that it yields correct stage sequence
    stages = [ev["stage"] for ev in events if ev["type"] == "stage"]
    assert "classifying" in stages
    assert "retrieving" in stages
    assert "verifying" in stages
    assert "generating" in stages
    
    # Check tokens and metadata
    tokens = [ev["token"] for ev in events if ev["type"] == "token"]
    assert len(tokens) > 0
    
    citations = [ev["citations"] for ev in events if ev["type"] == "citations"][0]
    assert isinstance(citations, list)
    
    trace = [ev["trace"] for ev in events if ev["type"] == "trace"][0]
    assert trace["intent"] == "fast"
    assert trace["workflow"] == "langgraph_multi_agent"
    assert trace["synthesis"]["citation_validation_passed"] is True

