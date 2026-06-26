"""Unit tests for Wikipedia parser and metadata mapper."""

import pytest
from app.services.ingestion.wikipedia_parser import parse_frontmatter, WikipediaParser


def test_parse_frontmatter_valid():
    markdown = (
        "---\n"
        "title: Cộng hòa miền Nam Việt Nam\n"
        "slug: cong-hoa-mien-nam-viet-nam\n"
        "type: organization\n"
        "aliases:\n"
        "  - Chính phủ lâm thời\n"
        "period:\n"
        "  start: 1969\n"
        "  end: 1976\n"
        "location:\n"
        "  - Miền Nam Việt Nam\n"
        "entities:\n"
        "  people:\n"
        "    - Nguyễn Hữu Thọ\n"
        "  organizations:\n"
        "    - Mặt trận Dân tộc Giải phóng\n"
        "  events:\n"
        "    - Chiến tranh Việt Nam\n"
        "---\n"
        "\n"
        "# Cộng hòa miền Nam Việt Nam\n"
        "Nội dung chính..."
    )
    
    meta, body = parse_frontmatter(markdown)
    assert meta["title"] == "Cộng hòa miền Nam Việt Nam"
    assert meta["slug"] == "cong-hoa-mien-nam-viet-nam"
    assert meta["type"] == "organization"
    assert meta["period"]["start"] == 1969
    assert meta["period"]["end"] == 1976
    assert "Chính phủ lâm thời" in meta["aliases"]
    assert "Miền Nam Việt Nam" in meta["location"]
    assert "Nguyễn Hữu Thọ" in meta["entities"]["people"]
    assert body.strip() == "# Cộng hòa miền Nam Việt Nam\nNội dung chính..."


def test_parse_frontmatter_invalid():
    markdown = "Không có frontmatter\n# Tiêu đề"
    meta, body = parse_frontmatter(markdown)
    assert meta == {}
    assert body == markdown


def test_map_frontmatter_to_metadata():
    parser = WikipediaParser()
    fm = {
        "title": "Cộng hòa miền Nam Việt Nam",
        "slug": "cong-hoa-mien-nam-viet-nam",
        "type": "organization",
        "aliases": ["Chính phủ lâm thời"],
        "period": {"start": 1969, "end": 1976},
        "location": ["Miền Nam Việt Nam"],
        "entities": {
            "people": ["Nguyễn Hữu Thọ"],
            "organizations": ["Mặt trận Dân tộc Giải phóng"],
            "events": ["Chiến tranh Việt Nam"],
        },
        "sources": ["Wikipedia Vietnamese"],
    }
    
    meta = parser.map_frontmatter_to_metadata(fm, "https://vi.wikipedia.org/wiki/Cộng_hòa_miền_Nam_Việt Nam")
    
    assert meta["title"] == "Cộng hòa miền Nam Việt Nam"
    assert meta["period"] == "1969-1976"
    assert meta["year"] == 1969
    assert meta["detected_years"] == [1969, 1976]
    assert meta["geographical_region"] == "Miền Nam Việt Nam"
    assert meta["entity_persons"] == ["Nguyễn Hữu Thọ"]
    assert meta["entity_organizations"] == ["Mặt trận Dân tộc Giải phóng"]
    assert meta["entity_events"] == ["Chiến tranh Việt Nam"]
    assert meta["source_type"] == "wikipedia"
    assert meta["confidence"] == 0.95
    assert meta["historical_metadata"]["slug"] == "cong-hoa-mien-nam-viet-nam"
