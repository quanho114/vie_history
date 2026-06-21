"""Unit tests for the ClaimExtractor service."""

import pytest
from app.services.citation.claim_extractor import ClaimExtractor

def test_split_sentences() -> None:
    extractor = ClaimExtractor()
    text = "Nguyễn Huệ lên ngôi Hoàng đế năm 1788. [S1] Sau đó ông đánh bại quân Thanh năm 1789. [S2]"
    sentences = extractor._split_sentences(text)
    assert len(sentences) == 2
    assert "1788" in sentences[0]
    assert "1789" in sentences[1]

def test_extract_subject() -> None:
    extractor = ClaimExtractor()
    assert extractor._extract_subject("Nguyễn Huệ lên ngôi Hoàng đế") == "Nguyễn Huệ"
    assert extractor._extract_subject("Vua Quang Trung dời đô") == "Vua Quang Trung"
    assert extractor._extract_subject("đánh bại quân Thanh") == ""

def test_claim_splitting_and_reconstruction() -> None:
    extractor = ClaimExtractor()
    text = "Nguyễn Huệ lên ngôi Hoàng đế năm 1788 và đánh bại quân Thanh năm 1789. [S1]"
    claims = extractor.extract_claims(text)
    
    assert len(claims) == 2
    assert claims[0]["text"] == "Nguyễn Huệ lên ngôi Hoàng đế năm 1788 [S1]"
    assert claims[0]["type"] == "temporal"  # contains 1788
    
    assert claims[1]["text"] == "Nguyễn Huệ đánh bại quân Thanh năm 1789 [S1]"
    assert claims[1]["type"] == "temporal"  # contains 1789

def test_claim_types() -> None:
    extractor = ClaimExtractor()
    assert extractor._infer_type("Nguyễn Huệ sinh năm 1753") == "temporal"
    assert extractor._infer_type("Quang Trung đánh trận tại Phú Xuân") == "location"
    assert extractor._infer_type("Vua Gia Long trị vì đất nước") == "actor"
    assert extractor._infer_type("Nhà Lê suy yếu do mâu thuẫn nội bộ") == "event"
