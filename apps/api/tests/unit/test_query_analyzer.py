import pytest
from app.services.agent.query_analyzer import QueryAnalyzer

@pytest.mark.asyncio
async def test_query_analyzer_parsing(mocker):
    # Mock LLM response to avoid network calls during tests
    mock_llm = mocker.patch("app.services.agent.query_analyzer.get_llm_client")
    mock_client = mocker.MagicMock()
    
    # Set up async mock response
    async def mock_generate(*args, **kwargs):
        return '{"intent": "cause_effect", "entities": ["nhà Hồ", "quân Minh"], "time_range": [1400, 1407]}'
    
    mock_client.generate = mock_generate
    mock_llm.return_value = mock_client

    analyzer = QueryAnalyzer()
    res = await analyzer.analyze("Tại sao nhà Hồ thất bại trước quân Minh năm 1407?")
    
    assert res["intent"] == "cause_effect"
    assert "nhà Hồ" in res["entities"]
    assert res["time_range"] == [1400, 1407]
