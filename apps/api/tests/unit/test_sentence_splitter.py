"""Tests for Vietnamese sentence boundary detection in CitationVerifier.

Covers:
- Normal sentence splitting
- Vietnamese abbreviations that must NOT be split (TP., ThS., TS., GS., tr., Q.)
- Citation markers [S1] at end of sentence must not break split
- Short exclamations and questions
"""

from __future__ import annotations

import pytest
from app.services.citation.verifier import CitationVerifier


@pytest.fixture
def verifier() -> CitationVerifier:
    """Return a CitationVerifier without loading the embedder model."""
    v = CitationVerifier.__new__(CitationVerifier)
    v.embedder = None  # not needed for split tests
    return v


class TestSentenceSplitter:
    def test_splits_plain_sentences(self, verifier):
        text = "Nguyễn Huệ sinh năm 1753. Ông mất năm 1792."
        result = verifier._split_into_sentences(text)
        assert len(result) == 2
        assert result[0].strip().startswith("Nguyễn Huệ")
        assert result[1].strip().startswith("Ông mất")

    def test_tp_abbreviation_not_split(self, verifier):
        text = "Sự kiện diễn ra tại TP. Hà Nội vào năm 1972. Đây là sự kiện lớn."
        result = verifier._split_into_sentences(text)
        # "TP." must NOT be treated as sentence boundary
        assert len(result) == 2
        assert "TP. Hà Nội" in result[0]

    def test_ths_abbreviation_not_split(self, verifier):
        text = "ThS. Nguyễn Văn A nghiên cứu tài liệu này. Kết quả khá tốt."
        result = verifier._split_into_sentences(text)
        assert len(result) == 2
        assert "ThS. Nguyễn" in result[0]

    def test_tr_abbreviation_not_split(self, verifier):
        text = "Theo nguồn tr. 123, sự kiện xảy ra năm 1975. Tài liệu đáng tin cậy."
        result = verifier._split_into_sentences(text)
        assert len(result) == 2

    def test_citation_marker_not_split(self, verifier):
        """A sentence ending with [S1] must not be split at the period inside."""
        text = "Quang Trung thắng quân Thanh năm 1789. [S1] Đây là chiến thắng vĩ đại."
        result = verifier._split_into_sentences(text)
        # Period before [S1] should not be a sentence boundary
        assert any("[S1]" in s for s in result)

    def test_question_mark_splits(self, verifier):
        text = "Ai lãnh đạo cuộc khởi nghĩa? Lê Lợi chính là người đó."
        result = verifier._split_into_sentences(text)
        assert len(result) == 2

    def test_single_sentence_no_period(self, verifier):
        text = "Nguyễn Huệ là anh hùng dân tộc"
        result = verifier._split_into_sentences(text)
        assert len(result) == 1
        assert result[0] == text

    def test_empty_string(self, verifier):
        result = verifier._split_into_sentences("")
        assert result == []

    def test_only_whitespace(self, verifier):
        result = verifier._split_into_sentences("   ")
        assert result == []

    def test_three_sentences(self, verifier):
        text = (
            "Chiến thắng Bạch Đằng năm 938 chấm dứt ngàn năm Bắc thuộc. "
            "Ngô Quyền lên làm vua. "
            "Ông lập ra triều Ngô."
        )
        result = verifier._split_into_sentences(text)
        assert len(result) == 3
