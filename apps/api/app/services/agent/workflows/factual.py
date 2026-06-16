"""Factual Workflow."""

from typing import Any
from app.core.logging import get_logger

logger = get_logger("factual_workflow")


class FactualWorkflow:
    """
    Workflow for factual queries.

    Steps:
    1. Extract entities (person, event, date)
    2. Hybrid search with entity + year filters
    3. Select top 5 evidence chunks
    4. Generate short grounded answer
    5. Attach citations
    """

    async def prepare_data(self, query: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Optional data preprocessing/sorting.
        For factual queries, we keep the top relevant chunks (up to 8) to keep answers concise.
        """
        logger.info("factual_workflow_prepare_data", query=query[:50], chunk_count=len(chunks))
        return chunks[:8]

    def get_prompts(self, query: str, chunks: list[dict[str, Any]]) -> tuple[str, str]:
        """
        Returns custom (system_prompt, user_prompt) matching the specific query intent.
        Directs LLM to give clean, short answers with direct citation markers [S1], [S2] etc.
        """
        system_prompt = (
            "Bạn là HistoriAI, trợ lý nghiên cứu lịch sử Việt Nam chuyên gia về giai đoạn 1945-1975.\n"
            "Nhiệm vụ của bạn là trả lời các câu hỏi tra cứu thực tế (factual queries) một cách trực tiếp, khách quan, chính xác và cực kỳ súc tích (ai, cái gì, ở đâu, khi nào).\n\n"
            "QUY TẮC TRÍCH DẪN NGHIÊM NGẶT:\n"
            "1. Chỉ sử dụng thông tin có trong phần SOURCES được cung cấp. Tuyệt đối không tự suy luận, bịa đặt thông tin ngoài nguồn.\n"
            "2. Mỗi dòng hoặc đoạn văn chứa thông tin lịch sử (không bắt đầu bằng các ký tự #, -, *) có độ dài từ 40 ký tự trở lên BẮT BUỘC phải kết thúc bằng ký hiệu trích dẫn dạng [S1], [S2] tương ứng với nguồn cung cấp thông tin để vượt qua khâu kiểm duyệt trích dẫn.\n"
            "3. Câu trả lời của bạn phải có ít nhất một đoạn văn tổng quan (không bắt đầu bằng ký tự danh sách #, -, *) có độ dài từ 40 ký tự trở lên và chứa trích dẫn nguồn cụ thể dạng [S1], [S2].\n"
            "4. Câu trả lời phải ngắn gọn, tập trung thẳng vào câu hỏi, tránh lan man dông dài."
        )

        source_blocks = []
        for index, chunk in enumerate(chunks, 1):
            title = chunk.get("document_title") or "Nguồn chưa đặt tên"
            section = chunk.get("section_title") or ""
            content = " ".join(chunk.get("content", "").split())[:1800]
            source_blocks.append(f"[S{index}] {title} {section}\n{content}")

        sources_text = "\n\n".join(source_blocks)

        user_prompt = (
            f"YÊU CẦU: Trả lời câu hỏi tra cứu thực tế lịch sử sau đây bằng tiếng Việt một cách trực tiếp, khách quan và súc tích:\n"
            f"CÂU HỎI: {query}\n\n"
            f"DANH SÁCH NGUỒN (SOURCES):\n"
            f"{sources_text}\n\n"
            f"Hãy viết câu trả lời ngắn gọn, tập trung chính xác vào câu hỏi. Hãy chắc chắn trích dẫn nguồn đầy đủ bằng [S1], [S2] ở cuối mỗi dòng/đoạn văn chứa câu khẳng định thực tế lịch sử."
        )

        return system_prompt, user_prompt

    async def execute(
        self,
        query: str,
        retrieval_service,
        llm_provider=None,
        filters: dict | None = None,
    ) -> dict:
        """Execute factual workflow."""
        logger.info("factual_workflow_execute", query=query[:50])

        # Step 1-2: Retrieve evidence
        chunks = await retrieval_service.hybrid_search(
            query=query,
            top_k=8,
            filters=filters,
        )

        processed_chunks = await self.prepare_data(query, chunks)
        system_prompt, user_prompt = self.get_prompts(query, processed_chunks)

        from app.agents.synthesizer import AnswerSynthesizer
        synthesizer = AnswerSynthesizer()
        synthesis_result = await synthesizer.synthesize(
            query=query,
            intent="factual",
            chunks=processed_chunks,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        return {
            "answer": synthesis_result.answer,
            "chunks": processed_chunks,
            "workflow": "factual",
            "used_llm": synthesis_result.used_llm,
        }


