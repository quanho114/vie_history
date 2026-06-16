import pytest
from app.services.agent.workflows.out_of_scope import OutOfScopeWorkflow

@pytest.mark.asyncio
async def test_out_of_scope_workflow_refusal_format():
    workflow = OutOfScopeWorkflow()
    res = await workflow.execute("bạn biết messi không?")
    assert "HistoriAI chuyên hỗ trợ nghiên cứu" in res["answer"]
    assert "Câu hỏi của bạn nằm ngoài phạm vi" in res["answer"]
    assert "Các triều đại Việt Nam" in res["answer"]
