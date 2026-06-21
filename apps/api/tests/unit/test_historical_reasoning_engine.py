import pytest
from app.services.agent.historical_reasoning_engine import HistoricalReasoningEngine

@pytest.mark.asyncio
async def test_historical_reasoning_engine(mocker):
    # Mock LLM client
    mock_llm = mocker.MagicMock()
    async def mock_generate(prompt, system=None, max_tokens=None):
        # Return a mocked causal JSON response
        return """{
            "causes": ["Hiệp định Sơ bộ bị phá vỡ", "Pháp mở rộng xung đột"],
            "triggers": ["Đêm 19/12/1946 tiếng súng kháng chiến bùng nổ tại Hà Nội"],
            "turning_points": ["Lời kêu gọi Toàn quốc kháng chiến của Chủ tịch Hồ Chí Minh"],
            "consequences": ["Cuộc chiến đấu giam chân địch trong các đô thị thành công"],
            "long_term_impacts": ["Bảo toàn lực lượng kháng chiến lâu dài và chuyển lên chiến khu Việt Bắc"]
        }"""
    
    mock_llm.generate = mock_generate
    mocker.patch("app.services.agent.historical_reasoning_engine.get_llm_client", return_value=mock_llm)
    
    engine = HistoricalReasoningEngine()
    
    # Run analysis
    analysis = await engine.analyze_causality(
        query="Tại sao toàn quốc kháng chiến bùng nổ năm 1946?",
        chunks=[{"content": "Ngày 19/12/1946, Chủ tịch Hồ Chí Minh ra Lời kêu gọi Toàn quốc kháng chiến."}],
        timeline_events=[{"year": "1946", "title": "Toàn quốc kháng chiến", "description": "Bùng nổ chiến sự"}]
    )
    
    assert "causes" in analysis
    assert "triggers" in analysis
    assert "turning_points" in analysis
    assert "consequences" in analysis
    assert "long_term_impacts" in analysis
    assert "Lời kêu gọi" in analysis["turning_points"][0]


@pytest.mark.asyncio
async def test_causal_reasoning_returns_rich_payload():
    """Verify that even when LLM calls fail or fallback is triggered, standard keys always exist."""
    engine = HistoricalReasoningEngine()
    
    # We verify structure output mapping
    result = await engine.analyze_causality(
        query="Tại sao nhà Hồ thất bại?",
        chunks=[{"content": "Nhà Hồ mất lòng dân nên bại trận."}]
    )
    
    # Even if LLM fails, standard keys must exist
    assert "causes" in result
    assert "triggers" in result
    assert "turning_points" in result
    assert "consequences" in result
    assert "long_term_impacts" in result

