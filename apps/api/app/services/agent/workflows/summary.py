"""Summary Workflow."""

from typing import Any
from app.core.logging import get_logger

logger = get_logger("summary_workflow")


class SummaryWorkflow:
    """
    Workflow for topic/event summary queries.

    Steps:
    1. Broad semantic search
    2. Multi-chunk selection
    3. Organize by subtopic
    4. Generate layered summary
    5. Attach citations per claim
    """

    async def prepare_data(self, query: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Optional data preprocessing/sorting.
        For summaries, we return a broad set of chunks (up to 12) to ensure a comprehensive overview.
        """
        logger.info("summary_workflow_prepare_data", query=query[:50], chunk_count=len(chunks))
        return chunks[:12]

    def get_prompts(self, query: str, chunks: list[dict[str, Any]]) -> tuple[str, str]:
        """
        Returns custom (system_prompt, user_prompt) directing LLM to write a layered summary
        starting with a high-level TL;DR overview paragraph, followed by sub-topics/headers
        with bullet points and strict citations.
        """
        system_prompt = (
            "Bạn là HistoriAI, trợ lý nghiên cứu lịch sử Việt Nam chuyên gia về giai đoạn 1945-1975.\n"
            "Nhiệm vụ của bạn là viết một bản tóm tắt phân lớp (layered summary) toàn diện và đa chiều về một chủ đề lịch sử.\n\n"
            "QUY TẮC CẤU TRÚC VÀ TRÍCH DẪN NGHIÊM NGẶT:\n"
            "1. MỞ ĐẦU bằng một đoạn văn tóm tắt cốt lõi (TL;DR overview paragraph) có độ dài ít nhất 40 ký tự, KHÔNG bắt đầu bằng các ký tự #, -, * và bắt buộc phải trích dẫn nguồn dạng [S1], [S2] để dẫn dắt câu trả lời.\n"
            "2. TIẾP THEO, chia nhỏ chủ đề thành các phần phụ/tiêu đề con (sub-topics/headers) hợp lý dựa trên nguồn tài liệu.\n"
            "3. Trong mỗi phần phụ, sử dụng các đầu dòng (bullet points) để tóm tắt chi tiết các khía cạnh khác nhau của chủ đề. Mỗi đầu dòng tóm tắt thông tin lịch sử cụ thể phải chứa trích dẫn nguồn tương ứng dạng [S1], [S2] ở cuối dòng.\n"
            "4. Tuyệt đối không đưa ý kiến cá nhân hoặc các thông tin nằm ngoài SOURCES."
        )

        source_blocks = []
        for index, chunk in enumerate(chunks, 1):
            title = chunk.get("document_title") or "Nguồn chưa đặt tên"
            section = chunk.get("section_title") or ""
            content = " ".join(chunk.get("content", "").split())[:1800]
            source_blocks.append(f"[S{index}] {title} {section}\n{content}")

        sources_text = "\n\n".join(source_blocks)

        user_prompt = (
            f"YÊU CẦU: Viết một bản tóm tắt phân lớp toàn diện về chủ đề lịch sử sau:\n"
            f"CHỦ ĐỀ: {query}\n\n"
            f"DANH SÁCH NGUỒN TÀI LIỆU (SOURCES):\n"
            f"{sources_text}\n\n"
            f"Hãy bắt đầu bằng một đoạn văn TL;DR tổng quan (có trích dẫn nguồn cụ thể dạng [S1], [S2]). Sau đó, chia nội dung thành các tiêu đề con logic và các gạch đầu dòng chi tiết chứa các trích dẫn nguồn tương ứng ở cuối mỗi câu/gạch đầu dòng."
        )

        return system_prompt, user_prompt

    async def execute(
        self,
        query: str,
        retrieval_service,
        llm_provider=None,
    ) -> dict:
        """Execute summary workflow."""
        logger.info("summary_workflow_execute", query=query[:50])

        # Step 1-2: Broad retrieval
        chunks = await retrieval_service.hybrid_search(
            query=query,
            top_k=10,
        )

        processed_chunks = await self.prepare_data(query, chunks)
        system_prompt, user_prompt = self.get_prompts(query, processed_chunks)

        from app.agents.synthesizer import AnswerSynthesizer
        synthesizer = AnswerSynthesizer()
        synthesis_result = await synthesizer.synthesize(
            query=query,
            intent="summary",
            chunks=processed_chunks,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        return {
            "answer": synthesis_result.answer,
            "summary": synthesis_result.answer,
            "chunks": processed_chunks,
            "workflow": "summary",
            "used_llm": synthesis_result.used_llm,
        }


