"""Metadata Extractor."""

import re
from datetime import datetime
from typing import Any

from app.core.logging import get_logger

logger = get_logger("metadata_extractor")


class MetadataExtractor:
    """
    Extract metadata from cleaned markdown content.
    Includes entity extraction and year detection.
    """

    KNOWN_DYNASTIES = {
        "Hồ": ["nhà Hồ", "Hồ Quý Ly", "Hồ Hán Thương"],
        "Nguyễn": ["nhà Nguyễn", "Gia Long", "Minh Mạng", "Thiệu Trị", "Tự Đức", "Bảo Đại", "triều Nguyễn"],
        "Lê": ["nhà Lê", "Lê Lợi", "Lê Thái Tổ", "Lê Thánh Tông", "Hậu Lê", "Lê triều"],
        "Trần": ["nhà Trần", "Trần Hưng Đạo", "Trần Thái Tông", "Trần Nhân Tông"],
        "Lý": ["nhà Lý", "Lý Thái Tổ", "Lý Thường Kiệt", "Lý Công Uẩn"],
        "Tây Sơn": ["Tây Sơn", "Nguyễn Huệ", "Quang Trung"]
    }
    
    KNOWN_REGIONS = {
        "Bắc Bộ": ["Bắc Bộ", "Đông Đô", "Thăng Long", "Hà Nội", "Bắc Kỳ"],
        "Trung Bộ": ["Trung Bộ", "Thuận Hóa", "Phú Xuân", "Huế", "Trung Kỳ"],
        "Nam Bộ": ["Nam Bộ", "Gia Định", "Sài Gòn", "Nam Kỳ"]
    }

    # Common Vietnamese historical figures
    KNOWN_PERSONS = [
        "Hồ Chí Minh",
        "Võ Nguyên Giáp",
        "Phạm Văn Đồng",
        "Trường Chinh",
        "Lê Duẩn",
        "Nguyễn Ái Quốc",
        "Nguyễn Huệ",
        "Trần Hưng Đạo",
        "Đinh Tiên Hoàng",
        "Lê Lợi",
    ]

    KNOWN_ORGANIZATIONS = [
        "Quân đội Nhân dân Việt Nam",
        "Việt Minh",
        "Đảng Cộng sản Việt Nam",
        "Chính phủ Việt Nam Dân chủ Cộng hòa",
        "Mặt trận Dân tộc Giải phóng miền Nam Việt Nam",
    ]

    # Vietnamese month names
    MONTH_MAP = {
        "tháng 1": 1, "tháng 2": 2, "tháng 3": 3, "tháng 4": 4,
        "tháng 5": 5, "tháng 6": 6, "tháng 7": 7, "tháng 8": 8,
        "tháng 9": 9, "tháng 10": 10, "tháng 11": 11, "tháng 12": 12,
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }

    def extract(self, markdown: str, title: str, source_url: str | None = None) -> dict[str, Any]:
        """
        Extract metadata from markdown.

        Returns:
            Dict with extracted metadata
        """
        logger.info("extracting_metadata", title=title[:50])

        # Detect years mentioned
        years = self._extract_years(markdown)

        # Detect entities
        entities = self._extract_entities(markdown)

        # Detect events
        events = self._detect_events(markdown)

        # Extract summary
        summary = self._extract_summary(markdown, title)

        # Generate tags
        tags = self._generate_tags(title, entities, years)

        # Determine source domain
        domain = None
        if source_url:
            try:
                from urllib.parse import urlparse
                domain = urlparse(source_url).netloc
            except Exception:
                pass

        # Determine period, year, event_type, confidence, and historical_metadata
        period = None
        year = None
        if years:
            sorted_years = sorted(list(years))
            year = sorted_years[0]
            # Heuristic for period
            if any(1945 <= y < 1954 for y in sorted_years):
                period = "1945-1954"
            elif any(1954 <= y <= 1975 for y in sorted_years):
                period = "1954-1975"
            else:
                period = "khac"

        # Determine event_type from keywords
        event_type = "cultural"
        markdown_lower = markdown.lower()
        if any(kw in markdown_lower for kw in ["hiệp định", "hội nghị", "đàm phán", "ký kết", "ngoại giao"]):
            event_type = "diplomatic"
        elif any(kw in markdown_lower for kw in ["chiến dịch", "trận đánh", "quân sự", "tấn công", "tiêu diệt", "bắn rơi", "súng", "lính"]):
            event_type = "military"
        elif any(kw in markdown_lower for kw in ["đảng", "chính phủ", "bầu cử", "tổng thống", "quốc hội", "chính trị"]):
            event_type = "political"

        # Determine confidence
        confidence = 0.5
        if years:
            confidence += 0.2
        if entities.get("persons") or entities.get("organizations"):
            confidence += 0.2
        if events:
            confidence += 0.1
        confidence = min(confidence, 1.0)

        # Extract dynasty and region (Rule-based)
        dynasty = None
        markdown_lower = markdown.lower()
        for dyn, keywords in self.KNOWN_DYNASTIES.items():
            if any(kw.lower() in markdown_lower for kw in keywords):
                dynasty = dyn
                break
                
        region = None
        for reg, keywords in self.KNOWN_REGIONS.items():
            if any(kw.lower() in markdown_lower for kw in keywords):
                region = reg
                break

        historical_metadata = {
            "primary_events": events,
            "extracted_at": datetime.now().isoformat(),
            "dynasty": dynasty,
            "geographical_region": region
        }

        return {
            "title": title,
            "source_url": source_url,
            "source_domain": domain,
            "summary": summary,
            "detected_years": sorted(list(years)) if years else None,
            "entity_persons": entities.get("persons") or None,
            "entity_places": entities.get("places") or None,
            "entity_organizations": entities.get("organizations") or None,
            "entity_events": events or None,
            "tags": tags,
            "period": period,
            "year": year,
            "dynasty": dynasty,
            "geographical_region": region,
            "event_type": event_type,
            "confidence": confidence,
            "historical_metadata": historical_metadata,
        }

    def _extract_years(self, text: str) -> set[int]:
        """Extract years mentioned in text (1945-1975 focus)."""
        years = set()
        year_pattern = r"\b(19[4-9][0-9])\b"
        matches = re.findall(year_pattern, text)

        for match in matches:
            year = int(match)
            if 1945 <= year <= 1975:
                years.add(year)

        return years

    def _extract_entities(self, text: str) -> dict[str, list[str]]:
        """Extract named entities (simplified)."""
        entities = {
            "persons": [],
            "places": [],
            "organizations": [],
        }

        # Check for known persons
        for person in self.KNOWN_PERSONS:
            if person in text:
                if person not in entities["persons"]:
                    entities["persons"].append(person)

        # Simple organization detection.
        for org in self.KNOWN_ORGANIZATIONS:
            if org in text and org not in entities["organizations"]:
                entities["organizations"].append(org)

        # Capitalized multi-word phrases for English/imported names.
        org_pattern = r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Đảng|Chính phủ|Quân|Tổ chức|Ban|Hội)\b"
        for match in re.finditer(org_pattern, text):
            org = match.group(0).strip()
            if org not in entities["organizations"]:
                entities["organizations"].append(org)

        # Simple place detection (province/city names)
        place_keywords = [
            "Hà Nội", "Hồ Chí Minh", "Đà Nẵng", "Huế", "Hải Phòng",
            "Cần Thơ", "Nha Trang", "Quảng Nam", "Thanh Hóa", "Nghệ An",
            "Hà Tĩnh", "Bắc Ninh", "Hưng Yên", "Nam Định", "Thái Bình",
            "Lạng Sơn", "Cao Bằng", "Lai Châu", "Sơn La", "Điện Biên",
        ]
        for place in place_keywords:
            if place in text and place not in entities["places"]:
                entities["places"].append(place)

        return entities

    def _detect_events(self, text: str) -> list[str]:
        """Detect historical events mentioned."""
        events = []

        event_keywords = [
            "Cách mạng tháng Tám",
            "Hiệp định Genève",
            "Hiệp định Paris",
            "Chiến dịch Điện Biên Phủ",
            "Tổng tiến công Tết Mậu Thân",
            "Sự kiện Tết Mậu Thân",
            "Cảnh cáo Mỹ",
            "Tổng tuyển cử",
            "Hiệp định",
            "Hội nghị",
            "Chiến tranh",
            "Đảo chính",
        ]

        for keyword in event_keywords:
            if keyword.lower() in text.lower() and keyword not in events:
                events.append(keyword)

        return events[:10]  # Limit to 10 events

    def _extract_summary(self, markdown: str, title: str) -> str:
        """Extract or generate summary from content."""
        # Get first paragraph after title
        paragraphs = markdown.split("\n\n")
        for para in paragraphs:
            para = para.strip()
            if len(para) > 100 and para != title:
                # Return first 500 chars
                return para[:500] + "..." if len(para) > 500 else para

        return ""

    def _generate_tags(
        self,
        title: str,
        entities: dict[str, list[str]],
        years: set[int],
    ) -> list[str]:
        """Generate tags for document."""
        tags = []

        # Add person tags
        tags.extend(entities.get("persons", [])[:3])

        # Add event tags
        tags.extend(entities.get("events", [])[:3])

        # Add year tags (decade level)
        if years:
            decade_tags = set()
            for year in years:
                decade = (year // 10) * 10
                decade_tags.add(f"{decade}s")
            tags.extend(list(decade_tags)[:3])

        # Deduplicate and limit
        seen = set()
        unique_tags = []
        for tag in tags:
            tag_lower = tag.lower()
            if tag_lower not in seen:
                seen.add(tag_lower)
                unique_tags.append(tag)

        return unique_tags[:10]  # Max 10 tags
