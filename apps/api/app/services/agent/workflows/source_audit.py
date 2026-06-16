"""Source Audit Workflow."""

from typing import Any
from app.core.logging import get_logger

logger = get_logger("source_audit_workflow")


class SourceAuditWorkflow:
    """
    Workflow for finding sources about a topic.

    Steps:
    1. Search raw evidence
    2. Rank documents by relevance
    3. Group chunks by document
    4. Return source-first answer
    """

    async def prepare_data(self, query: str, chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Group retrieved chunks by document and sort the chunks by document contribution.
        Ensure that the sources are ordered so the LLM can audit document contributions.
        """
        logger.info("source_audit_workflow_prepare_data", query=query[:50], chunk_count=len(chunks))

        # Group chunks by document (using title or id as key)
        doc_groups: dict[str, list[dict[str, Any]]] = {}
        for chunk in chunks:
            doc_key = chunk.get("document_title") or chunk.get("document_id") or "Nguồn chưa đặt tên"
            if doc_key not in doc_groups:
                doc_groups[doc_key] = []
            doc_groups[doc_key].append(chunk)

        # Rank documents by contribution chunk count, using average score as a tie-breaker
        sorted_docs = sorted(
            doc_groups.keys(),
            key=lambda k: (
                len(doc_groups[k]),
                sum(c.get("rerank_score", c.get("score", 0)) for c in doc_groups[k]) / len(doc_groups[k])
            ),
            reverse=True
        )

        # Build metadata and flatten chunks
        doc_stats = {}
        for rank, doc_key in enumerate(sorted_docs, 1):
            doc_stats[doc_key] = {
                "chunk_count": len(doc_groups[doc_key]),
                "rank": rank
            }

        ordered_chunks = []
        for doc_key in sorted_docs:
            for chunk in doc_groups[doc_key]:
                new_chunk = chunk.copy()
                stats = doc_stats[doc_key]
                new_chunk["doc_rank"] = stats["rank"]
                new_chunk["doc_chunk_count"] = stats["chunk_count"]
                ordered_chunks.append(new_chunk)

        return ordered_chunks

    def get_prompts(self, query: str, chunks: list[dict[str, Any]]) -> tuple[str, str]:
        """
        Returns custom (system_prompt, user_prompt) directing LLM to write a document-by-document
        source audit, describing what each source (Document) covers, its key contribution,
        and evidence, citing the corresponding sources [S1], [S2].
        """
        system_prompt = (
            "Bạn là HistoriAI, trợ lý nghiên cứu lịch sử Việt Nam chuyên gia về giai đoạn 1945-1975.\n"
            "Nhiệm vụ của bạn là thực hiện một bản kiểm định nguồn tài liệu (source audit) chi tiết dựa trên các tài liệu thu được.\n\n"
            "QUY TẮC CẤU TRÚC VÀ TRÍCH DẪN NGHIÊM NGẶT:\n"
            "1. BẮT ĐẦU bằng một đoạn giới thiệu tổng quan ngắn gọn (độ dài trên 40 ký tự, KHÔNG bắt đầu bằng các ký tự #, -, *) tóm tắt tổng số tài liệu nguồn nhận được và đóng góp chung của chúng, kèm theo trích dẫn nguồn rõ ràng dạng [S1], [S2] để mở đầu câu trả lời.\n"
            "2. Trình bày đánh giá/kiểm định theo từng tài liệu nguồn (document-by-document source audit) theo thứ tự mức độ đóng góp (Tài liệu Rank #1, #2, v.v.).\n"
            "3. Với mỗi tài liệu nguồn, hãy nêu rõ:\n"
            "   - Tên tài liệu/nguồn cụ thể\n"
            "   - Nội dung bao phủ chính của tài liệu đối với chủ đề\n"
            "   - Đóng góp cốt lõi của tài liệu (key contribution)\n"
            "   - Minh chứng/dẫn chứng cụ thể rút ra từ tài liệu, bắt buộc trích dẫn bằng ký hiệu [S1], [S2] tương ứng ở cuối câu/dòng chứa thông tin.\n"
            "4. Tuyệt đối không bịa đặt tên tài liệu hoặc thông tin lịch sử nằm ngoài SOURCES."
        )

        source_blocks = []
        for index, chunk in enumerate(chunks, 1):
            title = chunk.get("document_title") or "Nguồn chưa đặt tên"
            section = chunk.get("section_title") or ""
            doc_rank = chunk.get("doc_rank", 1)
            doc_count = chunk.get("doc_chunk_count", 1)
            content = " ".join(chunk.get("content", "").split())[:1800]
            source_blocks.append(
                f"[S{index}] [Tài liệu Rank #{doc_rank} - Đóng góp {doc_count} đoạn] {title} {section}\n{content}"
            )

        sources_text = "\n\n".join(source_blocks)

        user_prompt = (
            f"YÊU CẦU: Thực hiện kiểm định nguồn tài liệu chi tiết cho câu hỏi sau bằng tiếng Việt:\n"
            f"CÂU HỎI: {query}\n\n"
            f"DANH SÁCH NGUỒN TÀI LIỆU ĐÃ ĐƯỢC GỘP VÀ SẮP XẾP THEO ĐÓNG GÓP (SOURCES):\n"
            f"{sources_text}\n\n"
            f"Hãy bắt đầu bằng một đoạn giới thiệu tổng quan có trích dẫn nguồn (ví dụ: 'Các nguồn tài liệu thu thập được bao gồm... [S1]'), sau đó thực hiện kiểm định chi tiết từng tài liệu (bao gồm: Tên tài liệu, Nội dung bao phủ, Đóng góp cốt lõi, Minh chứng và dẫn chứng có trích dẫn rõ ràng dạng [S1], [S2])."
        )

        return system_prompt, user_prompt

    async def execute(
        self,
        query: str,
        retrieval_service,
        llm_provider=None,
    ) -> dict:
        """Execute source audit workflow."""
        logger.info("source_audit_workflow_execute", query=query[:50])

        # Step 1-3: Get chunks and group by document
        chunks = await retrieval_service.hybrid_search(
            query=query,
            top_k=15,
        )

        processed_chunks = await self.prepare_data(query, chunks)
        system_prompt, user_prompt = self.get_prompts(query, processed_chunks)

        from app.agents.synthesizer import AnswerSynthesizer
        synthesizer = AnswerSynthesizer()
        synthesis_result = await synthesizer.synthesize(
            query=query,
            intent="source_audit",
            chunks=processed_chunks,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )

        # Group by document for backward compatibility of execute return
        doc_sources: dict[str, list] = {}
        for chunk in processed_chunks:
            doc_id = chunk.get("document_id", "unknown")
            if doc_id not in doc_sources:
                doc_sources[doc_id] = []
            doc_sources[doc_id].append(chunk)

        # Rank documents by chunk count and average score
        ranked_sources = []
        for doc_id, doc_chunks in doc_sources.items():
            ranked_sources.append({
                "document_id": doc_id,
                "document_title": doc_chunks[0].get("document_title", "Unknown"),
                "source_url": doc_chunks[0].get("source_url"),
                "chunk_count": len(doc_chunks),
                "avg_score": sum(c.get("score", 0) for c in doc_chunks) / len(doc_chunks),
                "excerpts": [c.get("content", "")[:200] for c in doc_chunks[:3]],
            })

        ranked_sources.sort(key=lambda x: (x["chunk_count"], x["avg_score"]), reverse=True)

        return {
            "answer": synthesis_result.answer,
            "sources": ranked_sources,
            "chunks": processed_chunks,
            "workflow": "source_audit",
            "used_llm": synthesis_result.used_llm,
        }


