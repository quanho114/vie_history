"""Unit tests for metadata extractor."""

import pytest

from app.services.ingestion.metadata_extractor import MetadataExtractor


class TestExtractYears:
    """Year extraction tests."""

    def test_extracts_years_in_range(self) -> None:
        extractor = MetadataExtractor()
        text = "Cách mạng tháng Tám năm 1945. Chiến tranh kết thúc năm 1975."

        years = extractor._extract_years(text)

        assert 1945 in years
        assert 1975 in years

    def test_ignores_years_outside_range(self) -> None:
        extractor = MetadataExtractor()
        text = "Năm 1802, Nguyễn Huệ xưng đế. Năm 2025, hòa bình."

        years = extractor._extract_years(text)

        assert len(years) == 0

    def test_extracts_multiple_years(self) -> None:
        extractor = MetadataExtractor()
        text = "1945 1946 1947 1948 1949 1950 1954 1968 1975"

        years = extractor._extract_years(text)

        assert len(years) == 9
        assert 1945 in years
        assert 1954 in years


class TestExtractEntities:
    """Entity extraction tests."""

    def test_extracts_known_persons(self) -> None:
        extractor = MetadataExtractor()
        text = "Hồ Chí Minh là lãnh tụ. Võ Nguyên Giáp là tướng quân."

        entities = extractor._extract_entities(text)

        assert "Hồ Chí Minh" in entities["persons"]
        assert "Võ Nguyên Giáp" in entities["persons"]

    def test_extracts_places(self) -> None:
        extractor = MetadataExtractor()
        text = "Hà Nội là thủ đô. Đà Nẵng là thành phố lớn."

        entities = extractor._extract_entities(text)

        assert "Hà Nội" in entities["places"]
        assert "Đà Nẵng" in entities["places"]

    def test_extracts_organizations(self) -> None:
        extractor = MetadataExtractor()
        text = "Quân đội Nhân dân Việt Nam chiến đấu anh dũng."

        entities = extractor._extract_entities(text)

        assert len(entities["organizations"]) >= 1

    def test_no_duplicates_in_persons(self) -> None:
        extractor = MetadataExtractor()
        text = "Hồ Chí Minh. Hồ Chí Minh. Hồ Chí Minh."

        entities = extractor._extract_entities(text)

        assert entities["persons"].count("Hồ Chí Minh") == 1


class TestDetectEvents:
    """Event detection tests."""

    def test_detects_geneva_agreement(self) -> None:
        extractor = MetadataExtractor()
        text = "Hiệp định Genève được ký năm 1954."

        events = extractor._detect_events(text)

        assert "Hiệp định Genève" in events

    def test_detects_dien_bien_phu(self) -> None:
        extractor = MetadataExtractor()
        text = "Chiến dịch Điện Biên Phủ nổ ra năm 1954."

        events = extractor._detect_events(text)

        assert "Chiến dịch Điện Biên Phủ" in events

    def test_detects_tet_offensive(self) -> None:
        extractor = MetadataExtractor()
        text = "Tổng tiến công Tết Mậu Thân năm 1968."

        events = extractor._detect_events(text)

        assert "Tổng tiến công Tết Mậu Thân" in events

    def test_limits_to_10_events(self) -> None:
        extractor = MetadataExtractor()
        text = (
            "Cách mạng tháng Tám. Hiệp định Genève. Hiệp định Paris. "
            "Chiến dịch Điện Biên Phủ. Tổng tiến công Tết Mậu Thân. "
            "Cảnh cáo Mỹ. Tổng tuyển cử. Hội nghị. Chiến tranh. Đảo chính. "
            "Thêm sự kiện 1. Thêm sự kiện 2. Thêm sự kiện 3."
        )

        events = extractor._detect_events(text)

        assert len(events) <= 10


class TestExtractSummary:
    """Summary extraction tests."""

    def test_extracts_first_long_paragraph(self) -> None:
        extractor = MetadataExtractor()
        markdown = "Title\n\nShort.\n\n" + "A" * 150 + ".\n\nAnother paragraph."

        summary = extractor._extract_summary(markdown, "Title")

        assert len(summary) <= 503
        assert summary.startswith("A")

    def test_returns_empty_for_short_content(self) -> None:
        extractor = MetadataExtractor()
        markdown = "Title\n\nShort.\n\n" + "x" * 50

        summary = extractor._extract_summary(markdown, "Title")

        assert summary == ""

    def test_skips_title_in_summary(self) -> None:
        extractor = MetadataExtractor()
        title = "Trận Bạch Đằng"
        markdown = f"{title}\n\n{title} là một trận đánh lớn.\n\n" + "B" * 200 + "."

        summary = extractor._extract_summary(markdown, title)

        assert summary != title


class TestGenerateTags:
    """Tag generation tests."""

    def test_adds_person_tags(self) -> None:
        extractor = MetadataExtractor()
        entities = {"persons": ["Hồ Chí Minh", "Võ Nguyên Giáp"], "events": []}

        tags = extractor._generate_tags("Test", entities, set())

        assert "Hồ Chí Minh" in tags
        assert "Võ Nguyên Giáp" in tags

    def test_adds_decade_tags(self) -> None:
        extractor = MetadataExtractor()

        tags = extractor._generate_tags("Test", {"persons": [], "events": []}, {1945, 1968, 1975})

        assert "1940s" in tags
        assert "1960s" in tags
        assert "1970s" in tags

    def test_limits_tags_to_10(self) -> None:
        extractor = MetadataExtractor()
        entities = {
            "persons": ["Hồ Chí Minh", "Võ Nguyên Giáp", "Phạm Văn Đồng"],
            "events": [],
        }

        tags = extractor._generate_tags("Test", entities, {1945, 1954, 1968, 1975})

        assert len(tags) <= 10


class TestFullExtract:
    """Full metadata extraction tests."""

    def test_full_extraction_pipeline(self) -> None:
        extractor = MetadataExtractor()
        markdown = (
            "Hồ Chí Minh tuyên bố độc lập năm 1945 tại Hà Nội. "
            "Chiến dịch Điện Biên Phủ nổ ra năm 1954. "
            "Tổng tiến công Tết Mậu Thân năm 1968. "
        )
        title = "Lịch sử Việt Nam"
        url = "https://vi.wikipedia.org/wiki/Lịch_sử_Việt_Nam"

        result = extractor.extract(markdown, title, url)

        assert result["title"] == title
        assert result["source_domain"] == "vi.wikipedia.org"
        assert 1945 in (result["detected_years"] or [])
        assert 1954 in (result["detected_years"] or [])
        assert "Hồ Chí Minh" in (result["entity_persons"] or [])
        assert len(result["tags"]) > 0

    def test_handles_missing_url_gracefully(self) -> None:
        extractor = MetadataExtractor()

        result = extractor.extract("Content about history.", "Test", None)

        assert result["source_domain"] is None
        assert result["source_url"] is None

    def test_handles_empty_content(self) -> None:
        extractor = MetadataExtractor()

        result = extractor.extract("", "Test", None)

        assert result["detected_years"] is None
        assert result["entity_persons"] is None
        assert result["entity_places"] is None


class TestAcademicMetadata:
    """Academic metadata extraction tests."""

    def test_extracts_dynasty_and_region(self) -> None:
        extractor = MetadataExtractor()
        
        # Test Nguyễn dynasty & Trung Bộ region
        markdown = "Triều Nguyễn thành lập kinh đô Phú Xuân tại Huế thuộc miền Trung Bộ vào thế kỷ XIX."
        result = extractor.extract(markdown, "Triều Nguyễn")
        assert result["dynasty"] == "Nguyễn"
        assert result["geographical_region"] == "Trung Bộ"

        # Test Hồ dynasty & Bắc Bộ region
        markdown_ho = "Hồ Quý Ly dời đô về Tây Đô tại Bắc Bộ và lập ra nhà Hồ."
        result_ho = extractor.extract(markdown_ho, "Nhà Hồ")
        assert result_ho["dynasty"] == "Hồ"
        assert result_ho["geographical_region"] == "Bắc Bộ"

