"""Unit tests for deterministic intent classification."""

import pytest

from app.services.agent.classifier import IntentClassifier


@pytest.mark.asyncio
async def test_classifies_timeline_query() -> None:
    classifier = IntentClassifier()

    assert await classifier.classify("Diễn biến chiến dịch Điện Biên Phủ năm 1954") == "timeline"


@pytest.mark.asyncio
async def test_classifies_compare_query() -> None:
    classifier = IntentClassifier()

    assert await classifier.classify("So sánh Hiệp định Genève 1954 và Paris 1973") == "compare"


@pytest.mark.asyncio
async def test_classifies_out_of_scope_modern_year() -> None:
    classifier = IntentClassifier()

    assert await classifier.classify("Việt Nam năm 2026 có sự kiện gì?") == "out_of_scope"
