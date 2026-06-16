"""Unit tests for query metadata extractor."""

import pytest
from app.services.retrieval.query_metadata_extractor import extract_query_metadata

@pytest.mark.asyncio
async def test_extract_query_metadata_rule_based() -> None:
    # Test rule-based extraction
    res = await extract_query_metadata("Chính sách cải cách của nhà Hồ")
    assert res["dynasty"] == "Hồ"

    res_nguyen = await extract_query_metadata("Vua Gia Long triều Nguyễn làm gì?")
    assert res_nguyen["dynasty"] == "Nguyễn"

@pytest.mark.asyncio
async def test_extract_query_metadata_llm_mock(monkeypatch) -> None:
    # Mock LLM API call for queries without keywords
    class MockResponse:
        def __init__(self, json_data, status_code=200):
            self.json_data = json_data
            self.status_code = status_code
        def json(self):
            return self.json_data

    async def mock_post(*args, **kwargs):
        return MockResponse({
            "content": [{"text": '{"dynasty": "Hồ"}'}]
        })

    import httpx
    monkeypatch.setattr(httpx.AsyncClient, "post", mock_post)

    res = await extract_query_metadata("Chính sách cải cách đầu thế kỷ XV", api_key="test-key")
    assert res["dynasty"] == "Hồ"
