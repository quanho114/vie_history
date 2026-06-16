import pytest
from app.services.agent.workflows.out_of_scope import OutOfScopeWorkflow

@pytest.mark.asyncio
async def test_out_of_scope_workflow_refusal_format():
    workflow = OutOfScopeWorkflow()
    res = await workflow.execute("bạn biết messi không?")
    assert "Mình có thể hỗ trợ bạn tra cứu và phân tích" in res["answer"]
    assert "Ngoài lĩnh vực lịch sử Việt Nam, mình có thể không" in res["answer"]
    assert "Tóm tắt các sự kiện lịch sử" in res["answer"]
