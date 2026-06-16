# apps/api/tests/unit/test_classifier.py
import pytest
from app.services.agent.classifier import IntentClassifier


class TestIntentClassifier:
    """Unit tests for IntentClassifier."""

    @pytest.fixture
    def classifier(self):
        return IntentClassifier()

    @pytest.mark.asyncio
    async def test_classifies_factual_query(self, classifier):
        result = await classifier.classify("Ai là Chủ tịch Hồ Chí Minh?")
        assert result.intent == "factual"

    @pytest.mark.asyncio
    async def test_classifies_timeline_query(self, classifier):
        result = await classifier.classify("Diễn biến chiến dịch Điện Biên Phủ theo thứ tự thời gian?")
        assert result.intent == "timeline"

    @pytest.mark.asyncio
    async def test_classifies_out_of_scope(self, classifier):
        result = await classifier.classify("Thời tiết Hà Nội ngày mai thế nào?")
        assert result.intent == "out_of_scope"

    @pytest.mark.asyncio
    async def test_classifies_cause_effect(self, classifier):
        result = await classifier.classify("Tại sao Pháp thất bại ở Điện Biên Phủ?")
        assert result.intent == "cause_effect"
