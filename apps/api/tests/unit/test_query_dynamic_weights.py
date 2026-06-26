import pytest
from app.services.retrieval.query_service import QueryService

def test_dynamic_weights_factual_temporal() -> None:
    service = QueryService(
        embedder=None,
        vector_search=None,
        candidate_size=10,
        final_top_k=5,
        use_hyde=False
    )
    
    # Query with year digits
    w1 = service.calculate_dynamic_weights("Sự kiện năm 1945")
    assert w1["bm25"] == 0.7
    assert w1["vector"] == 0.3

    # Query with specific name keywords
    w2 = service.calculate_dynamic_weights("Chiến dịch Điện Biên Phủ ai chỉ huy")
    assert w2["bm25"] == 0.7
    assert w2["vector"] == 0.3

    # Query with location indicators
    w3 = service.calculate_dynamic_weights("Kinh đô triều Nguyễn ở đâu")
    assert w3["bm25"] == 0.7
    assert w3["vector"] == 0.3

def test_dynamic_weights_conceptual() -> None:
    service = QueryService(
        embedder=None,
        vector_search=None,
        candidate_size=10,
        final_top_k=5,
        use_hyde=False
    )
    
    # Query asking "tại sao"
    w1 = service.calculate_dynamic_weights("Tại sao nhà Hồ thất bại chống Minh")
    assert w1["vector"] == 0.8
    assert w1["bm25"] == 0.2

    # Query asking for comparisons
    w2 = service.calculate_dynamic_weights("So sánh quân đội nhà Trần và nhà Lý")
    assert w2["vector"] == 0.8
    assert w2["bm25"] == 0.2

    # Query asking for historical significance/impact
    w3 = service.calculate_dynamic_weights("Phân tích ý nghĩa lịch sử của Cách mạng tháng Tám")
    assert w3["vector"] == 0.8
    assert w3["bm25"] == 0.2

def test_dynamic_weights_default() -> None:
    service = QueryService(
        embedder=None,
        vector_search=None,
        candidate_size=10,
        final_top_k=5,
        use_hyde=False
    )
    
    # Balanced query
    w = service.calculate_dynamic_weights("Lịch sử Việt Nam")
    assert w["vector"] == 0.5
    assert w["bm25"] == 0.5
