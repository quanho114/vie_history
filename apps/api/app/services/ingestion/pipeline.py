"""Ingestion Pipeline Orchestrator."""

import re

from typing import Any

from app.core.logging import get_logger
from app.core.config import settings
from app.services.ingestion.url_validator import URLValidator
from app.services.ingestion.extractor import ContentExtractor
from app.services.ingestion.cleaner import ContentCleaner
from app.services.ingestion.metadata_extractor import MetadataExtractor

logger = get_logger("ingestion_pipeline")


class IngestionPipeline:
    """
    Orchestrates the full URL ingestion pipeline.

    Steps:
    1. URL validation + SSRF check
    2. Content fetching
    3. Content extraction
    4. Cleaning
    5. Markdown conversion
    6. Metadata extraction
    7. Quality validation
    """

    def __init__(self):
        self.url_validator = URLValidator()
        self.extractor = ContentExtractor()
        self.cleaner = ContentCleaner()
        self.metadata_extractor = MetadataExtractor()

    async def process_url(self, url: str, tags: list[str] | None = None) -> dict[str, Any]:
        """
        Process a URL through the full ingestion pipeline.

        Args:
            url: URL to ingest
            tags: Optional tags for the document

        Returns:
            Dict with processing results
        """
        logger.info("pipeline_start", url=url[:100])
        stages = []

        # Stage 1: URL Validation
        try:
            validation = self.url_validator.validate(url)
            if not validation["valid"]:
                return {
                    "success": False,
                    "error": validation["error"],
                    "stage": "url_validation",
                    "url": url,
                }
            url = validation["normalized"]
            stages.append("url_validation")
        except Exception as e:
            logger.error("url_validation_error", error=str(e))
            return {
                "success": False,
                "error": str(e),
                "stage": "url_validation",
                "url": url,
            }

        # Stage 2: Content Fetching
        raw_html = None
        try:
            fetched = await self.extractor.fetch(url)
            raw_html = fetched["html"]
            stages.append("fetching")
        except ValueError as e:
            return {
                "success": False,
                "error": str(e),
                "stage": "fetching",
                "url": url,
            }

        # Stage 3: Content Extraction
        extracted_text = None
        source_title = fetched.get("title", "") or ""
        try:
            # Clean HTML first
            cleaned_html = self.cleaner.clean_html(raw_html)

            # Convert to markdown
            markdown = self.cleaner.convert_to_markdown(cleaned_html)

            # Clean markdown
            markdown = self.cleaner.clean_markdown(markdown)

            # Restructure using LLM if available
            markdown = await self.restructure_markdown_with_llm(source_title, markdown)

            extracted_text = markdown
            stages.append("extraction")
        except Exception as e:
            logger.error("extraction_error", error=str(e))
            return {
                "success": False,
                "error": f"Extraction failed: {str(e)}",
                "stage": "extraction",
                "url": url,
            }

        # Stage 4: Metadata Extraction
        metadata = {}
        try:
            metadata = self.metadata_extractor.extract(
                markdown=extracted_text,
                title=source_title,
                source_url=url,
            )
            if tags:
                metadata["tags"] = list(set(metadata.get("tags", []) + tags))
            stages.append("metadata_extraction")
        except Exception as e:
            logger.error("metadata_error", error=str(e))
            # Continue with empty metadata

        # Stage 5: Quality Validation
        is_valid, error_msg = self.cleaner.validate_content(extracted_text)
        stages.append("quality_validation")

        if not is_valid:
            logger.warning("quality_check_failed", error=error_msg)
            return {
                "success": False,
                "error": error_msg,
                "stage": "quality_validation",
                "url": url,
            }

        # Stage 6: Source Type Detection
        source_type = self.extractor.detect_source_type(url, raw_html)
        metadata["source_type"] = source_type

        logger.info("pipeline_success", stages=stages, title=source_title[:50])

        return {
            "success": True,
            "url": url,
            "title": source_title,
            "markdown": extracted_text,
            "html": raw_html,
            "metadata": metadata,
            "stages": stages,
        }

    def chunk_text(
        self,
        markdown: str,
        chunk_size: int | None = None,
        overlap: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Split markdown into chunks for indexing.

        Args:
            markdown: Markdown text to chunk
            chunk_size: Target chunk size in tokens
            overlap: Overlap between chunks

        Returns:
            List of chunk dicts with content and metadata
        """
        chunk_size = chunk_size or settings.CHUNK_SIZE_TOKENS
        overlap = overlap or settings.CHUNK_OVERLAP_TOKENS

        chunks = []
        sections = self._split_by_heading(markdown)

        current_chunk = []
        current_size = 0
        chunk_index = 0

        for section in sections:
            section_size = len(section["content"].split())
            section_title = section.get("title")

            # If single section is too large, split by paragraph
            if section_size > chunk_size // 4:
                paragraphs = section["content"].split("\n\n")
                for para in paragraphs:
                    para_size = len(para.split())

                    if current_size + para_size > chunk_size and current_chunk:
                        # Save current chunk
                        chunks.append({
                            "index": chunk_index,
                            "title": current_chunk[0].get("title") if current_chunk else None,
                            "content": "\n\n".join(c["text"] for c in current_chunk),
                        })
                        chunk_index += 1

                        # Start new chunk with overlap
                        overlap_texts = [c["text"] for c in current_chunk[-2:]]
                        current_chunk = []
                        for ot in overlap_texts:
                            current_chunk.append({
                                "title": section_title,
                                "text": ot,
                            })
                            current_size = len(ot.split())

                    current_chunk.append({
                        "title": section_title,
                        "text": para,
                    })
                    current_size += para_size
            else:
                # Add section to current chunk
                if current_size + section_size > chunk_size and current_chunk:
                    chunks.append({
                        "index": chunk_index,
                        "title": current_chunk[0].get("title") if current_chunk else None,
                        "content": "\n\n".join(c["text"] for c in current_chunk),
                    })
                    chunk_index += 1

                    # Overlap
                    overlap_texts = [c["text"] for c in current_chunk[-2:]]
                    current_chunk = []
                    for ot in overlap_texts:
                        current_chunk.append({
                            "title": section_title,
                            "text": ot,
                        })
                    current_size = sum(len(t.split()) for t in overlap_texts)

                current_chunk.append({
                    "title": section_title,
                    "text": section["content"],
                })
                current_size += section_size

        # Save last chunk
        if current_chunk:
            chunks.append({
                "index": chunk_index,
                "title": current_chunk[0].get("title") if current_chunk else None,
                "content": "\n\n".join(c["text"] for c in current_chunk),
            })

        return chunks

    def _split_by_heading(self, markdown: str) -> list[dict[str, str]]:
        """Split markdown by headings."""
        lines = markdown.split("\n")
        sections = []
        current_section = {"title": None, "content": ""}

        for line in lines:
            # Check for heading
            heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if heading_match:
                # Save previous section
                if current_section["content"].strip():
                    sections.append(current_section)

                current_section = {
                    "title": heading_match.group(2).strip(),
                    "content": "",
                }
            else:
                current_section["content"] += line + "\n"

        # Save last section
        if current_section["content"].strip():
            sections.append(current_section)

        return sections

    async def restructure_markdown_with_llm(self, title: str, markdown: str) -> str:
        """
        Restructure already-cleaned markdown into polished academic prose using LLM.

        The pre-filtering stage in ContentCleaner.clean_markdown() handles boilerplate
        removal. This step focuses purely on:
          - Academic tone and prose quality
          - Logical section ordering  
          - Converting raw data clusters into Markdown tables
          - Filling any remaining structural gaps
        """
        try:
            from app.services.llm.client import get_llm_client, MockLLMClient
            llm = get_llm_client()
            if isinstance(llm, MockLLMClient) or len(markdown) <= 100:
                return markdown

            logger.info("llm_restructuring_start", title=title[:50])

            system_prompt = (
                "Bạn là một học giả lịch sử chuyên biên soạn tài liệu học thuật chuẩn.\n\n"
                "NHIỆM VỤ: Tái cấu trúc văn bản lịch sử đã được tiền xử lý thành bài viết học thuật hoàn chỉnh.\n\n"
                "QUY TẮC BẮT BUỘC:\n"
                "1. GIỮ NGUYÊN mọi sự kiện, ngày tháng, tên người, địa danh — không thêm, không bịa.\n"
                "2. CẤU TRÚC TIÊU ĐỀ: Dùng # cho tiêu đề bài, ## cho chương, ### cho mục.\n"
                "3. VĂN PHONG: Học thuật, trang trọng, trôi chảy. Không dùng từ thông tục.\n"
                "4. BẢNG BIỂU: Chuyển mọi dữ liệu so sánh (lực lượng, thương vong, niên đại) thành bảng Markdown.\n"
                "   Ví dụ: | Bên | Quân số | Tổn thất |\n"
                "5. LOẠI BỎ tàn dư boilerplate nếu còn: dòng '- x - t - s', 'Bài chi tiết:', 'Xem thêm:', icon portal.\n"
                "6. GỘP đoạn văn rời rạc cùng chủ đề thành đoạn mạch lạc.\n"
                "7. KHÔNG thêm lời dẫn, tiêu đề phụ 'Kết luận', hay bất kỳ nội dung nào ngoài bài.\n"
                "8. ĐẦU RA: Chỉ trả về nội dung Markdown thuần túy, bắt đầu bằng # Tiêu đề.\n"
            )

            prompt = (
                f"Tái cấu trúc tài liệu lịch sử sau thành bài học thuật chuẩn:\n\n"
                f"**Tiêu đề:** {title}\n\n"
                f"---\n\n"
                f"{markdown}"
            )

            structured_markdown = await llm.generate(
                prompt=prompt,
                system=system_prompt,
                max_tokens=8000,
            )
            if structured_markdown and len(structured_markdown.strip()) > 100:
                logger.info("llm_restructuring_success", title=title[:50])
                return structured_markdown.strip()
        except Exception as e:
            logger.warning("llm_restructuring_failed", error=str(e))
        return markdown
