"""RAG-Fusion: Multi-query generation + Reciprocal Rank Fusion.

Reference: "RAG-Fusion: a New Take on Retrieval-Augmented Generation"
(Zackary Rackauckas, 2024)

Pipeline:
1. LLM generates N query variations (synonyms, rephrasings, angles)
2. Each variation goes through hybrid search (vector + BM25)
3. All results fused with RRF
4. Cross-encoder reranking
"""

from __future__ import annotations

from typing import Any

import asyncio

from app.core.logging import get_logger
from app.services.llm.client import get_llm_client
from app.services.retrieval.fusion import FusionSearch

logger = get_logger("rag_fusion")

QUERY_VARIATION_PROMPT = """Bạn là chuyên gia nghiên cứu lịch sử Việt Nam.

Với câu hỏi nghiên cứu sau, hãy tạo {n} biến thể truy vấn khác nhau:
1. Mỗi biến thể diễn đạt cùng một ý từ góc nhìn hoặc cách diễn đạt khác
2. Sử dụng các từ đồng nghĩa, cách hỏi khác
3. Một số biến thể nên hỏi về khía cạnh cụ thể hơn

Câu hỏi gốc: {query}

Trả về danh sách biến thể, mỗi biến thể trên một dòng, không đánh số, không giải thích:
"""


class RAGFusionService:
    """
    RAG-Fusion: Multi-query expansion with RRF.

    Generates query variations to improve recall on complex questions.
    Particularly effective for:
    - Historical queries with multiple valid phrasings
    - Queries about events with alternate names
    - Complex multi-aspect questions
    """

    def __init__(
        self,
        query_service: "QueryService | None" = None,
        num_variations: int = 3,
        fusion: FusionSearch | None = None,
    ):
        self._query_service = query_service
        self.num_variations = num_variations
        self.fusion = fusion or FusionSearch(rrf_k=60)

    @property
    def query_service(self):
        """Lazy-load QueryService to avoid circular imports at module init."""
        if self._query_service is None:
            from app.services.retrieval.query_service import QueryService
            self._query_service = QueryService()
        return self._query_service

    async def generate_query_variations(self, query: str) -> list[str]:
        """Generate N query variations using LLM."""
        llm = get_llm_client()
        prompt = QUERY_VARIATION_PROMPT.format(
            n=self.num_variations,
            query=query,
        )

        try:
            response = await llm.generate(
                prompt,
                system="Bạn là chuyên gia nghiên cứu lịch sử Việt Nam.",
                max_tokens=256,
            )

            # Parse variations (one per line)
            variations = [
                line.strip()
                for line in response.strip().split("\n")
                if line.strip() and len(line.strip()) > 10
            ]

            # Always include original query
            all_queries = [query] + variations[: self.num_variations]
            logger.info("query_variations_generated", count=len(all_queries), original=query[:50])

            return all_queries

        except Exception as exc:
            logger.warning("query_variation_failed", error=str(exc))
            return [query]  # Fallback to original

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
    ) -> list[dict[str, Any]]:
        """
        RAG-Fusion search pipeline:
        1. Generate query variations
        2. Parallel hybrid search for each variation
        3. RRF fusion
        4. Return top_k results
        """
        # 1. Generate variations
        variations = await self.generate_query_variations(query)

        # 2. Parallel hybrid search for each variation
        search_tasks = [
            self.query_service.hybrid_search(
                q,
                top_k=top_k * 2,  # Fetch more to compensate for fusion
                filters=filters,
                skip_rerank=True,  # Skip reranking until after fusion
            )
            for q in variations
        ]

        search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

        # 3. Collect all results
        all_results: dict[str, dict[str, Any]] = {}
        for variation_idx, results in enumerate(search_results):
            if isinstance(results, Exception):
                logger.warning("variation_search_failed", idx=variation_idx, error=str(results))
                continue
            if not isinstance(results, list):
                continue

            for result in results:
                doc_id = result.get("id") or result.get("chunk_id") or str(result.get("content", "")[:100])
                if doc_id not in all_results:
                    all_results[doc_id] = {
                        **result,
                        "fusion_count": 0,
                        "variation_ranks": [],
                    }
                all_results[doc_id]["fusion_count"] += 1
                all_results[doc_id]["variation_ranks"].append(variation_idx)

        # 4. Score by fusion count (documents retrieved by more variations rank higher)
        for doc_id, doc in all_results.items():
            # Boost: fusion_count indicates cross-variation relevance
            boost = doc["fusion_count"] / len(variations)
            base_score = doc.get("score", 0.5)
            doc["fusion_score"] = base_score + (boost * 0.3)

        # Sort by fusion score
        fused = sorted(
            all_results.values(),
            key=lambda x: x.get("fusion_score", 0),
            reverse=True,
        )

        # 5. Apply Vietnamese reranker to top candidates
        try:
            from app.services.retrieval.cross_encoder_reranker import CrossEncoderReranker, get_reranker
            reranker = get_reranker()
            if reranker is not None and reranker.is_available:
                top_candidates = fused[:top_k * 3]  # Top 3x for reranking
                reranked = reranker.rerank(query, top_candidates, top_k=top_k)

                logger.info(
                    "rag_fusion_complete",
                    query=query[:50],
                    variations=len(variations),
                    unique_docs=len(all_results),
                    final_results=len(reranked),
                )
                return reranked
            else:
                return fused[:top_k]
        except ImportError:
            logger.warning("reranker_not_available_rag_fusion")
            return fused[:top_k]
        except Exception as rerank_exc:
            logger.warning("fusion_reranking_failed", error=str(rerank_exc))
            return fused[:top_k]

    async def rag_fusion_stream(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
    ):
        """
        Streaming RAG-Fusion with progressive results.
        Yields results as they become available.
        """
        variations = await self.generate_query_variations(query)
        yield {"type": "variations", "variations": variations, "count": len(variations)}

        # Parallel search with progress
        tasks = {}
        for idx, q in enumerate(variations):
            tasks[f"search_{idx}"] = self.query_service.hybrid_search(
                q, top_k=top_k * 2, filters=filters, skip_rerank=True
            )

        # Yield results as they complete
        done_count = 0
        for coro in asyncio.as_completed(tasks.values()):
            result = await coro
            done_count += 1
            yield {"type": "search_progress", "completed": done_count, "total": len(variations)}
