"""Wikipedia Normalization Parser and Schema Enricher."""

import re
import yaml
from datetime import datetime
from typing import Any

from app.core.logging import get_logger
from app.services.llm.client import get_llm_client, MockLLMClient

logger = get_logger("wikipedia_parser")


def parse_frontmatter(markdown_content: str) -> tuple[dict[str, Any], str]:
    """
    Extract and parse YAML frontmatter from a markdown string.
    
    Returns:
        A tuple of (metadata_dict, clean_markdown_body)
    """
    # Match YAML frontmatter between --- and ---
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", markdown_content, re.DOTALL)
    if match:
        yaml_content = match.group(1)
        body_content = markdown_content[match.end():]
        try:
            metadata = yaml.safe_load(yaml_content)
            if isinstance(metadata, dict):
                return metadata, body_content
        except Exception as e:
            logger.warning("failed_to_parse_frontmatter_yaml", error=str(e))
    return {}, markdown_content


class WikipediaParser:
    """
    Parses and enriches raw Wikipedia markdown into the Historical Markdown Schema.
    """

    async def normalize_to_schema(self, title: str, raw_markdown: str, url: str) -> str:
        """
        Use the LLM to enrich raw Wikipedia markdown into the target Historical Markdown Schema.
        
        Ensures the original text is preserved while adding the YAML frontmatter 
        and organizing sections under standardized headings.
        """
        try:
            llm = get_llm_client()
            if isinstance(llm, MockLLMClient) or len(raw_markdown) <= 100:
                logger.info("skip_llm_normalization_mock_or_short_content")
                return raw_markdown

            logger.info("wikipedia_schema_normalization_start", title=title[:50])

            system_prompt = (
                "Bạn là một chuyên gia chuẩn hóa dữ liệu lịch sử và biên soạn tài liệu học thuật.\n"
                "NHIỆM VỤ: Chuyển đổi nội dung bài viết Wikipedia tiếng Việt đã được làm sạch thành bài viết lịch sử chuẩn hóa theo schema quy định bên dưới.\n\n"
                "QUY TẮC BẮT BUỘC:\n"
                "1. GIỮ NGUYÊN nội dung chi tiết của các phần lịch sử, sự kiện, năm tháng, tên người, bảng biểu — KHÔNG được tóm tắt hay tự ý loại bỏ thông tin chi tiết.\n"
                "2. CẤU TRÚC TIÊU ĐỀ: Phải chuẩn hóa bài viết theo cấu trúc các tiêu đề sau (tiêu đề # chỉ xuất hiện 1 lần duy nhất ở đầu):\n"
                "   # <Tiêu đề bài viết>\n"
                "   ## Tổng quan\n"
                "   ## Lịch sử hình thành\n"
                "     ### Bối cảnh\n"
                "     ### Thành lập\n"
                "   ## Cơ cấu tổ chức\n"
                "     ### Lãnh đạo\n"
                "   ## Sự kiện liên quan\n"
                "   ## Quan hệ với thực thể khác\n"
                "     ### Quan hệ chính trị\n"
                "   ## Kết thúc tồn tại\n"
                "   ## Tài liệu tham khảo\n"
                "   (Nếu mục nào không có dữ liệu trong văn bản gốc, hãy để trống hoặc ghi nhận ngắn gọn dựa trên văn bản, không tự bịa thông tin).\n"
                "3. BẢNG BIỂU: Giữ nguyên hoặc chuyển đổi các niên biểu/sự kiện thành bảng Markdown chuẩn: | Năm | Sự kiện | Ý nghĩa |\n"
                "4. FRONTMATTER: Bắt buộc chèn khối YAML frontmatter ở đầu bài viết (bắt đầu bằng --- và kết thúc bằng ---) theo định dạng chính xác sau (không dùng cặp thẻ ```yaml để bao quanh frontmatter):\n"
                "---\n"
                "title: <Tiêu đề bài viết>\n"
                "slug: <slug tiếng Việt không dấu, ví dụ: cong-hoa-mien-nam-viet-nam>\n"
                "type: <Loại thực thể: organization, person, event, location, hoặc khác>\n"
                "aliases:\n"
                "  - <Tên gọi khác 1>\n"
                "  - <Tên gọi khác 2>\n"
                "period:\n"
                "  start: <Năm bắt đầu, số nguyên hoặc null>\n"
                "  end: <Năm kết thúc, số nguyên hoặc null>\n"
                "location:\n"
                "  - <Địa danh 1>\n"
                "  - <Địa danh 2>\n"
                "entities:\n"
                "  people:\n"
                "    - <Nhân vật liên quan 1>\n"
                "  organizations:\n"
                "    - <Tổ chức liên quan 1>\n"
                "  events:\n"
                "    - <Sự kiện liên quan 1>\n"
                "sources:\n"
                "  - Wikipedia Vietnamese\n"
                "---\n"
            )

            prompt = (
                f"Hãy chuẩn hóa tài liệu Wikipedia sau đây theo cấu trúc Historical Markdown Schema và trích xuất YAML frontmatter:\n\n"
                f"**Tiêu đề:** {title}\n"
                f"**URL:** {url}\n\n"
                f"---\n\n"
                f"{raw_markdown}"
            )

            enriched_markdown = await llm.generate(
                prompt=prompt,
                system=system_prompt,
                max_tokens=8000,
            )
            if enriched_markdown and len(enriched_markdown.strip()) > 100:
                logger.info("wikipedia_schema_normalization_success", title=title[:50])
                return enriched_markdown.strip()
        except Exception as e:
            logger.error("wikipedia_schema_normalization_failed", error=str(e))
        return raw_markdown

    def map_frontmatter_to_metadata(self, fm: dict[str, Any], url: str) -> dict[str, Any]:
        """
        Map the YAML frontmatter fields to Document database/metadata columns.
        """
        title = fm.get("title") or ""
        slug = fm.get("slug") or ""
        source_type = fm.get("type") or "wikipedia"
        aliases = fm.get("aliases") or []
        
        # Period start/end years
        period_data = fm.get("period") or {}
        start_year = None
        end_year = None
        if isinstance(period_data, dict):
            start_year = period_data.get("start")
            end_year = period_data.get("end")
        
        detected_years = []
        if isinstance(start_year, int):
            detected_years.append(start_year)
        elif isinstance(start_year, str) and start_year.isdigit():
            detected_years.append(int(start_year))
            
        if isinstance(end_year, int):
            detected_years.append(end_year)
        elif isinstance(end_year, str) and end_year.isdigit():
            detected_years.append(int(end_year))
            
        location = fm.get("location") or []
        if isinstance(location, str):
            location = [location]
        
        entities = fm.get("entities") or {}
        persons = entities.get("people") or []
        orgs = entities.get("organizations") or []
        events = entities.get("events") or []

        # Determine year (primary)
        year = None
        if detected_years:
            year = detected_years[0]

        # Determine period string
        period_str = None
        if start_year is not None and end_year is not None:
            period_str = f"{start_year}-{end_year}"
        elif start_year is not None:
            period_str = f"{start_year}-"
        elif end_year is not None:
            period_str = f"-{end_year}"

        # Geographical region
        region = ", ".join(location) if isinstance(location, list) else str(location)

        # Map to historical_metadata
        historical_metadata = {
            "slug": slug,
            "aliases": aliases,
            "type": source_type,
            "period": period_data,
            "location": location,
            "entities": entities,
            "sources": fm.get("sources") or ["Wikipedia Vietnamese"],
            "primary_events": events,
            "extracted_at": datetime.now().isoformat(),
        }

        # Event type heuristic
        event_type = "historical"
        if source_type == "event":
            event_type = "military" if any(kw in title.lower() for kw in ["chiến", "trận", "tấn công"]) else "political"

        return {
            "title": title,
            "source_url": url,
            "summary": fm.get("summary") or f"Bài viết Wikipedia về {title}.",
            "detected_years": detected_years or None,
            "entity_persons": persons or None,
            "entity_places": location or None,
            "entity_organizations": orgs or None,
            "entity_events": events or None,
            "tags": list(set([source_type] + aliases[:3] + location[:2])),
            "period": period_str,
            "year": year,
            "dynasty": fm.get("dynasty"),
            "geographical_region": region or None,
            "event_type": event_type,
            "confidence": 0.95,
            "historical_metadata": historical_metadata,
            "source_type": "wikipedia",
        }
