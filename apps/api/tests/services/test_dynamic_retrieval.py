import pytest
from app.services.retrieval.query_service import QueryService

@pytest.mark.asyncio
async def test_dynamic_weights():
    # Setup QueryService with dummy parameters as tests/unit mocks or Nones
    qs = QueryService(None, None, None)
    w_fact = qs.calculate_dynamic_weights("Chiến dịch Hồ Chí Minh giải phóng Sài Gòn vào ngày tháng năm nào?")
    assert w_fact["bm25"] > w_fact["vector"]
    
    w_concept = qs.calculate_dynamic_weights("Tại sao nước Việt Nam lại giành được độc lập và bài học so sánh với các nước khác?")
    assert w_concept["vector"] > w_concept["bm25"]
