"""Contextual Retrieval — augment chunks with LLM-generated context.

Reference: Anthropic, "Contextual Retrieval" (2024)

Before embedding a chunk, use an LLM to generate a brief context statement
explaining how this chunk relates to the overall document. This helps:
1. Disambiguate chunks that make sense in isolation but have unclear context
2. Improve retrieval precision for chunks about specific events
3. Better handle Vietnamese historical terms that have multiple meanings
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.core.logging import get_logger
from app.services.llm.client import get_llm_client

logger = get_logger("contextual_retrieval")

CONTEXTUALIZE_PROMPT = """Bạn là chuyên gia tạo ngữ cảnh tìm kiếm.

Dưới đây là một đoạn văn bản từ tài liệu lịch sử Việt Nam.

ĐOẠN VĂN BẢN:
{chunk}

NGỮ CẢNH TÀI LIỆU (nếu có):
{document_summary}

NHIỆM VỤ:
Viết một câu ngữ cảnh ngắn (2-3 câu) giải thích:
1. Đoạn này thuộc chủ đề/sự kiện lịch sử nào
2. Mối liên hệ với nội dung tổng thể của tài liệu
3. Vai trò của đoạn này trong câu chuyện lịch sử

Viết bằng tiếng Việt, ngắn gọn, trực tiếp.
"""


class ContextualRetrievalAugmenter:
    """
    Augments document chunks with LLM-generated context.

    Process:
    1. Generate document-level summary (one-time per document)
    2. For each chunk, generate contextual description
    3. Prepend context to chunk content for embedding
    4. Store augmented chunks in vector DB

    Benefit: ~20% retrieval quality improvement on ambiguous queries.
    """

    def __init__(self, batch_size: int = 10):
        self.batch_size = batch_size

    async def contextualize_chunks(
        self,
        chunks: list[dict[str, Any]],
        document_summary: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Augment chunks with contextual descriptions.

        Returns chunks with additional 'contextualized_content' field
        that combines the context with the original content.
        """
        if not chunks:
            return chunks

        # Generate document summary if not provided
        if not document_summary:
            document_summary = await self._generate_document_summary(chunks)

        # Generate context for each chunk in batches
        augmented = []
        for i in range(0, len(chunks), self.batch_size):
            batch = chunks[i:i + self.batch_size]
            batch_tasks = [
                self._contextualize_chunk(chunk, document_summary)
                for chunk in batch
            ]
            batch_results = await asyncio.gather(*batch_tasks, return_exceptions=True)

            for chunk, result in zip(batch, batch_results):
                chunk = dict(chunk)  # Copy
                if isinstance(result, Exception):
                    chunk["contextualized_content"] = chunk.get("content", "")
                    chunk["context_error"] = str(result)
                else:
                    chunk["contextualized_content"] = result
                augmented.append(chunk)

        return augmented

    async def _generate_document_summary(self, chunks: list[dict[str, Any]]) -> str:
        """Generate a brief document summary for context."""
        # Combine first few chunks as representative sample
        sample = "\n\n".join([
            c.get("content", "")[:500] for c in chunks[:3]
        ])

        llm = get_llm_client()
        prompt = f"""Tóm tắt tài liệu lịch sử Việt Nam sau đây trong 2-3 câu:

{sample}

Trả về bản tóm tắt ngắn gọn bằng tiếng Việt:"""

        try:
            return await llm.generate(prompt, system="Bạn là chuyên gia nghiên cứu lịch sử.", max_tokens=150)
        except Exception:
            return "Tài liệu lịch sử Việt Nam."

    async def _contextualize_chunk(
        self,
        chunk: dict[str, Any],
        document_summary: str,
    ) -> str:
        """Generate context for a single chunk."""
        llm = get_llm_client()
        prompt = CONTEXTUALIZE_PROMPT.format(
            chunk=chunk.get("content", "")[:1500],
            document_summary=document_summary,
        )

        try:
            context = await llm.generate(
                prompt,
                system="Bạn là chuyên gia tạo ngữ cảnh tìm kiếm.",
                max_tokens=100,
            )

            # Combine: context + separator + original content
            return f"[Ngữ cảnh: {context.strip()}] {chunk.get('content', '')}"
        except Exception as exc:
            logger.warning("contextualize_chunk_failed", error=str(exc))
            return chunk.get("content", "")

    async def contextualize_and_index(
        self,
        document_id: str,
        chunks: list[dict[str, Any]],
        vector_search: "VectorSearch | None" = None,
    ) -> int:
        """
        Full contextual retrieval pipeline:
        1. Contextualize chunks
        2. Embed contextualized content
        3. Index in Qdrant
        """
        if vector_search is None:
            from app.services.retrieval.vector_search import VectorSearch
            vector_search = VectorSearch()

        # 1. Contextualize
        augmented = await self.contextualize_chunks(chunks)

        # 2. Embed contextualized content (if embedder available)
        try:
            from app.services.retrieval.embedder import Embedder
            embedder = Embedder()
            texts = [c["contextualized_content"] for c in augmented]
            embeddings = embedder.embed(texts)

            # 3. Prepare chunks with embeddings
            for idx, chunk in enumerate(augmented):
                chunk["content"] = chunk["contextualized_content"]  # Use augmented
                chunk["embedding"] = embeddings[idx].tolist() if hasattr(embeddings[idx], 'tolist') else embeddings[idx]
                chunk["document_id"] = document_id

            # Index in vector DB
            await vector_search.index_chunks(augmented)
        except Exception as exc:
            logger.error("contextualize_index_failed", error=str(exc))
            # Fallback: just return augmented chunks without indexing
            pass

        logger.info("contextualize_and_index_complete", document_id=document_id, chunks=len(augmented))
        return len(augmented)
