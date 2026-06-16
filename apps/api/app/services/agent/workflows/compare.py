"""Compare Workflow."""

import re
from typing import Any
from app.core.logging import get_logger

logger = get_logger("compare_workflow")


class CompareWorkflow:
    """
    Workflow for comparison queries.

    Steps:
    1. Parse subject A and B
    2. Two parallel retrieval plans
    3. Independent evidence gathering
    4. Side-by-side comparison structure
    5. Return comparison format
    """

    async def prepare_data(self, query: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Identify comparison subjects from the query and label chunks.
        Ensure the sources list clearly labels Subject A vs Subject B chunks
        so the LLM can make distinct comparative citations.
        """
        logger.info("compare_workflow_prepare_data", query=query[:50], chunk_count=len(chunks))

        # Parse subjects from query
        subjects = []
        clean_query = query.lower()
        for prefix in ["so sánh", "sự khác nhau giữa", "khác biệt giữa", "so sánh giữa", "điểm giống và khác nhau giữa"]:
            if clean_query.startswith(prefix):
                clean_query = clean_query[len(prefix):].strip()
                break

        # Try splitting by 'và', 'với', 'vs'
        parts = re.split(r'\bvà\b|\bvới\b|\bvs\b', clean_query)
        if len(parts) >= 2:
            subjects = [p.strip().capitalize() for p in parts[:2]]
        else:
            subjects = ["Đối tượng A", "Đối tượng B"]

        subject_a = subjects[0]
        subject_b = subjects[1]

        # Extract keywords for matching
        def get_keywords(subject: str) -> list[str]:
            words = [w.strip(",.!?\"'") for w in subject.lower().split()]
            return [w for w in words if len(w) > 2]

        keywords_a = get_keywords(subject_a)
        keywords_b = get_keywords(subject_b)

        labeled_chunks = []
        for chunk in chunks:
            content_lower = chunk.get("content", "").lower()
            title_lower = chunk.get("document_title", "").lower()

            matches_a = sum(1 for kw in keywords_a if kw in content_lower or kw in title_lower)
            matches_b = sum(1 for kw in keywords_b if kw in content_lower or kw in title_lower)

            new_chunk = chunk.copy()
            if matches_a > matches_b:
                new_chunk["subject_label"] = f"Liên quan đến {subject_a}"
            elif matches_b > matches_a:
                new_chunk["subject_label"] = f"Liên quan đến {subject_b}"
            else:
                new_chunk["subject_label"] = "Chung / Liên quan đến cả hai"

            labeled_chunks.append(new_chunk)

        return labeled_chunks

    def get_prompts(self, query: str, chunks: list[dict[str, Any]]) -> tuple[str, str]:
        """
        Returns custom (system_prompt, user_prompt) directing LLM to write a structured comparison,
        outlining bối cảnh (context), điểm giống nhau (similarities), điểm khác biệt (differences),
        and ý nghĩa (significance), using proper comparative citations.
        """
        system_prompt = (
            "Bạn là HistoriAI, trợ lý nghiên cứu lịch sử Việt Nam chuyên gia về giai đoạn 1945-1975.\n"
            "Nhiệm vụ của bạn là phân tích và so sánh đối chiếu (comparison analysis) giữa hai sự kiện, hiệp định hoặc đối tượng lịch sử.\n\n"
            "QUY TẮC CẤU TRÚC VÀ TRÍCH DẪN NGHIÊM NGẶT:\n"
            "1. BẮT ĐẦU bằng một đoạn văn giới thiệu tổng quan ngắn gọn (độ dài trên 40 ký tự, KHÔNG bắt đầu bằng các ký tự #, -, *) nêu rõ hai đối tượng so sánh và có kèm trích dẫn nguồn rõ ràng dạng [S1], [S2] để mở đầu câu trả lời.\n"
            "2. Cấu trúc câu trả lời rõ ràng gồm 4 phần chính:\n"
            "   - Bối cảnh lịch sử\n"
            "   - Điểm giống nhau\n"
            "   - Điểm khác biệt\n"
            "   - Ý nghĩa lịch sử\n"
            "3. Mỗi nhận định, phân tích hoặc điểm giống/khác biệt phải trích dẫn nguồn rõ ràng bằng ký hiệu [S1], [S2] tương ứng ở cuối mỗi dòng/đoạn văn chứa câu khẳng định lịch sử.\n"
            "4. Tuyệt đối chỉ sử dụng các thông tin xác thực từ SOURCES được cung cấp, không suy diễn ngoài nguồn."
        )

        source_blocks = []
        for index, chunk in enumerate(chunks, 1):
            title = chunk.get("document_title") or "Nguồn chưa đặt tên"
            section = chunk.get("section_title") or ""
            label = chunk.get("subject_label", "Chung")
            content = " ".join(chunk.get("content", "").split())[:1800]
            source_blocks.append(f"[S{index}] [Nhãn phân loại: {label}] {title} {section}\n{content}")

        sources_text = "\n\n".join(source_blocks)

        user_prompt = (
            f"YÊU CẦU: So sánh hai đối tượng lịch sử sau đây dựa trên nguồn tài liệu được cung cấp:\n"
            f"CÂU HỎI/SO SÁNH: {query}\n\n"
            f"DANH SÁCH NGUỒN ĐÃ ĐƯỢC PHÂN LOẠI (SOURCES):\n"
            f"{sources_text}\n\n"
            f"Hãy bắt đầu bằng một đoạn giới thiệu tổng quan có trích dẫn nguồn (ví dụ: 'Bài viết dưới đây thực hiện so sánh... [S1]'), sau đó trình bày so sánh cấu trúc theo 4 phần: Bối cảnh lịch sử, Điểm giống nhau, Điểm khác biệt, Ý nghĩa lịch sử. Mỗi nhận định so sánh phải ghi rõ trích dẫn nguồn tương ứng bằng dạng [S1], [S2]."
        )

        return system_prompt, user_prompt

    async def execute(
        self,
        query: str,
        retrieval_service,
        llm_provider=None,
        subjects: list[str] | None = None,
    ) -> dict:
        """Execute compare workflow."""
        logger.info("compare_workflow_execute", query=query[:50], subjects=subjects)

        if not subjects or len(subjects) < 2:
            # Try parsing subjects from query
            clean_query = query.lower()
            for prefix in ["so sánh", "sự khác nhau giữa", "khác biệt giữa", "so sánh giữa", "điểm giống và khác nhau giữa"]:
                if clean_query.startswith(prefix):
                    clean_query = clean_query[len(prefix):].strip()
                    break

            parts = re.split(r'\bvà\b|\bvới\b|\bvs\b', clean_query)
            if len(parts) >= 2:
                subjects = [p.strip().capitalize() for p in parts[:2]]
            else:
                subjects = ["Đối tượng A", "Đối tượng B"]

        # Parallel retrieval
        chunks_a = await retrieval_service.hybrid_search(
            query=subjects[0],
            top_k=5,
        )

        chunks_b = await retrieval_service.hybrid_search(
            query=subjects[1],
            top_k=5,
        )

        all_chunks = chunks_a + chunks_b
        processed_chunks = await self.prepare_data(query, all_chunks)
        system_prompt, user_prompt = self.get_prompts(query, processed_chunks)

        from app.agents.synthesizer import AnswerSynthesizer
        synthesizer = AnswerSynthesizer()
        synthesis_result = await synthesizer.synthesize(
            query=query,
            intent="compare",
            chunks=processed_chunks,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # Build comparison dict for backwards compatibility
        comparison = {
            "subjects": subjects,
            "aspects": {
                "Tên nguồn dẫn chính": {
                    subjects[0]: chunks_a[0].get("document_title", "N/A") if chunks_a else "N/A",
                    subjects[1]: chunks_b[0].get("document_title", "N/A") if chunks_b else "N/A",
                },
            },
        }

        return {
            "answer": synthesis_result.answer,
            "comparison": comparison,
            "chunks": processed_chunks,
            "workflow": "compare",
            "used_llm": synthesis_result.used_llm,
        }


