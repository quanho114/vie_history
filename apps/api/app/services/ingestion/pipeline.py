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
        source_title = ""
        try:
            # Clean HTML first
            cleaned_html = self.cleaner.clean_html(raw_html)

            # Convert to markdown
            markdown = self.cleaner.convert_to_markdown(cleaned_html)

            # Clean markdown
            markdown = self.cleaner.clean_markdown(markdown)

            extracted_text = markdown
            source_title = fetched.get("title", "")
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
