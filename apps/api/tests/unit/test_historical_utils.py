"""Unit tests for Vietnamese historical search expansion utilities."""

from app.services.retrieval.historical_utils import (
    normalize_vietnamese_text,
    expand_historical_query,
)


def test_normalize_vietnamese_text() -> None:
    """Ensure tone marks and casing are successfully stripped."""
    assert normalize_vietnamese_text("Nguyễn Huệ") == "nguyen hue"
    assert normalize_vietnamese_text("Lý Thường Kiệt") == "ly thuong kiet"
    assert normalize_vietnamese_text("Mậu Thân") == "mau than"


def test_expand_historical_query_entity() -> None:
    """Ensure name aliases are expanded correctly in historical queries."""
    query = "Tiểu sử của Hồ Thơm"
    expanded = expand_historical_query(query)
    
    assert "Hồ Thơm" in expanded
    assert "Quang Trung" in expanded
    assert "Nguyễn Huệ" in expanded
    assert "Bắc Bình Vương" in expanded


def test_expand_historical_query_can_chi() -> None:
    """Ensure Can Chi calendar years are expanded to solar years in queries."""
    query = "Sự kiện năm Kỷ Dậu"
    expanded = expand_historical_query(query)
    
    assert "Kỷ Dậu" in expanded
    assert "1789" in expanded
    assert "1969" in expanded


def test_expand_historical_query_combined() -> None:
    """Ensure combined query expansions perform optimally."""
    query = "Chiến thắng năm Kỷ Dậu của Quang Trung"
    expanded = expand_historical_query(query)
    
    assert "Quang Trung" in expanded
    assert "Nguyễn Huệ" in expanded
    assert "Kỷ Dậu" in expanded
    assert "1789" in expanded
