"""Timeline Workflow."""

import re
from typing import Any
from app.core.logging import get_logger

logger = get_logger("timeline_workflow")


class TimelineWorkflow:
    """
    Workflow for timeline queries.

    Steps:
    1. Extract year range + topic
    2. Year-bounded retrieval
    3. Group chunks by year
    4. Deduplicate events
    5. Generate chronological structure
    6. Return timeline format
    """

    async def prepare_data(self, query: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Extract years/dates from each chunk's content (using regex matching 1940-2000)
        and sort the chunks chronologically by their extracted years.
        """
        logger.info("timeline_workflow_prepare_data", query=query[:50], chunk_count=len(chunks))
        year_pattern = re.compile(r"\b(1[4-9]\d{2}|20[1-9]\d|21[0-2]\d)\b")

        chunks_with_year = []
        for chunk in chunks:
            content = chunk.get("content", "")
            title = chunk.get("document_title", "")
            # Check both content and document title for year indicators
            matches = year_pattern.findall(content) + year_pattern.findall(title)
            if matches:
                years = [int(y) for y in matches]
                min_year = min(years)
            else:
                min_year = 9999  # Put chunks without years at the end
            chunks_with_year.append((min_year, chunk))

        # Sort chronologically by the extracted year
        chunks_with_year.sort(key=lambda x: x[0])

        # Return sorted chunks
        return [item[1] for item in chunks_with_year]

    def get_prompts(self, query: str, chunks: list[dict[str, Any]]) -> tuple[str, str]:
        """
        Returns custom (system_prompt, user_prompt) directing LLM to build a chronological
        sequence structure using Markdown lists, clearly showing mốc năm (years) and citation markers.
        """
        system_prompt = (
            "Bạn là HistoriAI, trợ lý nghiên cứu lịch sử Việt Nam chuyên gia về giai đoạn 1945-1975.\n"
            "Nhiệm vụ của bạn là xây dựng một niên biểu/tiến trình lịch sử (chronological timeline) một cách khoa học, rõ ràng và chính xác.\n\n"
            "QUY TẮC CẤU TRÚC VÀ TRÍCH DẪN NGHIÊM NGẶT:\n"
            "1. BẮT ĐẦU bằng một đoạn văn giới thiệu tổng quan ngắn gọn (độ dài trên 40 ký tự, KHÔNG bắt đầu bằng các ký tự #, -, *) tóm tắt tiến trình và có kèm trích dẫn nguồn rõ ràng dạng [S1], [S2] để mở đầu câu trả lời.\n"
            "2. Xây dựng các sự kiện theo thứ tự thời gian tăng dần (từ quá khứ đến sau này). Sử dụng danh sách liệt kê rõ ràng chỉ rõ mốc năm (years).\n"
            "3. Mỗi sự kiện/mốc năm cụ thể trong danh sách phải mô tả ngắn gọn diễn biến chính và bắt buộc trích dẫn nguồn chứa thông tin đó dưới dạng [S1], [S2] tương ứng ở cuối mỗi câu/dòng có chứa claim.\n"
            "4. Tuyệt đối chỉ dùng thông tin trong SOURCES được cung cấp. Không tự thêm thắt mốc thời gian hay sự kiện ngoài nguồn."
        )

        source_blocks = []
        for index, chunk in enumerate(chunks, 1):
            title = chunk.get("document_title") or "Nguồn chưa đặt tên"
            section = chunk.get("section_title") or ""
            content = " ".join(chunk.get("content", "").split())[:1800]
            source_blocks.append(f"[S{index}] {title} {section}\n{content}")

        sources_text = "\n\n".join(source_blocks)

        user_prompt = (
            f"YÊU CẦU: Xây dựng niên biểu lịch sử theo trình tự thời gian cho câu hỏi sau bằng tiếng Việt:\n"
            f"CÂU HỎI: {query}\n\n"
            f"DANH SÁCH NGUỒN ĐÃ SẮP XẾP THEO TIẾN TRÌNH THỜI GIAN (SOURCES):\n"
            f"{sources_text}\n\n"
            f"Hãy bắt đầu bằng một đoạn giới thiệu tổng quan có trích dẫn nguồn (ví dụ: 'Dưới đây là niên biểu lịch sử... [S1]'), sau đó liệt kê các mốc sự kiện lịch sử theo thứ tự thời gian tăng dần, ghi rõ mốc năm ở đầu mỗi sự kiện, và trích dẫn đầy đủ nguồn tương ứng bằng dạng [S1], [S2]."
        )

        return system_prompt, user_prompt

    async def execute(
        self,
        query: str,
        retrieval_service,
        llm_provider=None,
        filters: dict | None = None,
    ) -> dict:
        """Execute timeline workflow."""
        logger.info("timeline_workflow_execute", query=query[:50])

        # Step 1-2: Retrieve evidence with year filter
        chunks = await retrieval_service.hybrid_search(
            query=query,
            top_k=20,
            filters=filters,
        )

        processed_chunks = await self.prepare_data(query, chunks)
        system_prompt, user_prompt = self.get_prompts(query, processed_chunks)

        from app.agents.synthesizer import AnswerSynthesizer
        synthesizer = AnswerSynthesizer()
        synthesis_result = await synthesizer.synthesize(
            query=query,
            intent="timeline",
            chunks=processed_chunks,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # Parse basic events from chunks or synthesized text for compatibility
        events = []
        import re
        year_pattern = re.compile(r"\b(1[4-9]\d{2}|20[1-9]\d|21[0-2]\d)\b")
        for chunk in processed_chunks[:5]:
            content = chunk.get("content", "")
            matches = year_pattern.findall(content)
            if matches:
                year = int(matches[0])
                # Simple sentence split to get a short description
                sentences = [s.strip() for s in content.split(".") if s.strip()]
                description = sentences[0] if sentences else content[:100]
                events.append({
                    "year": year,
                    "title": chunk.get("document_title", "Sự kiện lịch sử"),
                    "description": description
                })
        
        events.sort(key=lambda x: x["year"])

        return {
            "answer": synthesis_result.answer,
            "events": events,
            "chunks": processed_chunks,
            "workflow": "timeline",
            "used_llm": synthesis_result.used_llm,
        }


