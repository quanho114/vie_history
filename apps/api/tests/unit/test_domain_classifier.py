import pytest
from unittest.mock import AsyncMock, patch
from app.agents.domain_classifier import DomainClassifier, DomainDecision

@pytest.mark.asyncio
async def test_classify_rules_out_of_scope():
    classifier = DomainClassifier()
    res = classifier.classify_rules("bạn biết messi không?")
    assert res is not None
    assert res.decision == DomainDecision.OUT_OF_SCOPE
    assert res.source == "rule"

@pytest.mark.asyncio
async def test_classify_rules_in_scope():
    classifier = DomainClassifier()
    res = classifier.classify_rules("Hiệp định Giơ-nê-vơ năm 1954")
    assert res is not None
    assert res.decision == DomainDecision.IN_SCOPE
    assert res.source == "rule"

@pytest.mark.asyncio
async def test_classify_rules_ambiguous():
    classifier = DomainClassifier()
    # Ambiguous query that doesn't trigger rules
    res = classifier.classify_rules("bạn làm cái gì thế")
    assert res is None

@pytest.mark.asyncio
async def test_classify_llm_fail_closed_unknown():
    classifier = DomainClassifier()
    # Force LLM generation failure (simulated timeout)
    with patch("app.agents.domain_classifier.get_llm_client", side_effect=Exception("Timeout")):
        res = await classifier.classify_llm("truy vấn mơ hồ")
        assert res.decision == DomainDecision.UNKNOWN
        assert res.source == "fallback"
