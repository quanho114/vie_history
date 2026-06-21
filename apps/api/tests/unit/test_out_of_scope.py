import pytest
from app.services.agent.workflows.out_of_scope import OutOfScopeWorkflow

@pytest.mark.asyncio
async def test_out_of_scope_workflow_refusal_format():
    workflow = OutOfScopeWorkflow()
    res = await workflow.execute("bạn biết messi không?")
    assert "trợ lý chuyên sâu về Lịch sử Việt Nam" in res["answer"]
    assert "để đảm bảo độ chính xác cao nhất" in res["answer"]
    assert "Nếu bạn có câu hỏi nào về Lịch sử Việt Nam" in res["answer"]
