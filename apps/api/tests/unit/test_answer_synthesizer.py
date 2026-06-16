"""Tests for grounded synthesis fallback and citation validation."""

import pytest

from app.agents.synthesizer import AnswerSynthesizer


@pytest.mark.asyncio
async def test_extractive_fallback_adds_source_markers() -> None:
    synthesizer = AnswerSynthesizer()

    result = await synthesizer.synthesize(
        query="Điện Biên Phủ có ý nghĩa gì?",
        intent="factual",
        chunks=[
            {
                "document_title": "Điện Biên Phủ",
                "content": "Chiến dịch Điện Biên Phủ kết thúc thắng lợi năm 1954 và tác động lớn tới cục diện đàm phán.",
            }
        ],
    )

    assert "[S1]" in result.answer
    assert result.used_llm is False


def test_validation_rejects_uncited_claim_line() -> None:
    synthesizer = AnswerSynthesizer()

    assert synthesizer._validate_answer("Đây là một câu lịch sử dài nhưng không có nguồn trích dẫn rõ ràng.") is not None


def test_validation_accepts_cited_claim_line() -> None:
    synthesizer = AnswerSynthesizer()

    assert synthesizer._validate_answer("Chiến dịch kết thúc năm 1954 theo nguồn được cung cấp. [S1]") is None
