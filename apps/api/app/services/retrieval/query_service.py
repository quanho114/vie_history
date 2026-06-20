"""Query service combining retrieval methods.

Pipeline:
    Query
      -> Vector Search (Qdrant)
      -> Elasticsearch BM25 (lexical)
      -> Reciprocal Rank Fusion (RRF)
      -> Cross-encoder Reranking (precision boost)
      -> Top-K Results
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.logging import get_logger
from app.services.retrieval.embedder import Embedder
from app.services.retrieval.vector_search import VectorSearch
from app.services.retrieval.fusion import FusionSearch

if TYPE_CHECKING:
    from app.services.retrieval.cross_encoder_reranker import CrossEncoderReranker
    from app.services.retrieval.meilisearch_bm25 import MeilisearchBM25

logger = get_logger("query_service")


class QueryService:
    """
    Combined query service using two-stage hybrid retrieval + reranking.

    Stage 1 — First-stage retrieval (high recall):
        - Vector search (Qdrant) for semantic similarity
        - Elasticsearch BM25 for exact keyword matching
        - Reciprocal Rank Fusion combines both ranked lists

    Stage 2 — Second-stage reranking (high precision):
        - Cross-encoder scores every candidate (query, document) pair
        - Blends cross-encoder score with first-stage RRF score
        - Returns the top-K most precise results

    Args:
        embedder: Embedding service (default: Embedder singleton)
        vector_search: Qdrant vector search service
        es_bm25: Elasticsearch BM25 service (optional — in-memory fallback if unavailable)
        reranker: Cross-encoder reranker (optional — falls back to lexical if unavailable)
        fusion: RRF fusion service
        candidate_size: How many candidates to fetch from first-stage
            (larger = more candidates for reranker, better precision, more latency)
        final_top_k: How many results to return after reranking
    """

    def __init__(
        self,
        embedder: Embedder | None = None,
        vector_search: VectorSearch | None = None,
        meili_bm25: MeilisearchBM25 | None = None,
        reranker: CrossEncoderReranker | None = None,
        fusion: FusionSearch | None = None,
        candidate_size: int = 20,
        final_top_k: int = 5,
        use_hyde: bool = True,
    ):
        self.embedder = embedder or Embedder()
        self.vector_search = vector_search or VectorSearch()
        self.meili_bm25 = meili_bm25
        self.reranker = reranker
        self.fusion = fusion or FusionSearch(rrf_k=60)
        self.candidate_size = candidate_size
        self.final_top_k = final_top_k
        self.use_hyde = use_hyde
        self._hyde: Any | None = None

    async def _ensure_meili_bm25(self):
        """Lazy-init Meilisearch BM25 if configured and not yet initialized."""
        if self.meili_bm25 is None:
            await self._ensure_meili_bm25_with_retry()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,)),
    )
    async def _ensure_meili_bm25_with_retry(self):
        """Retry-wrapped Meilisearch BM25 initialization."""
        try:
            from app.services.retrieval.meilisearch_bm25 import get_meilisearch_bm25
            self.meili_bm25 = await get_meilisearch_bm25()
            logger.info("meili_bm25_attached")
        except Exception as exc:
            logger.warning("meili_bm25_unavailable", error=str(exc))
            self.meili_bm25 = None
            raise  # re-raise so tenacity can retry

    async def _ensure_reranker(self):
        """Lazy-init cross-encoder reranker if not yet initialized."""
        if self.reranker is None:
            await self._ensure_reranker_with_retry()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((Exception,)),
    )
    async def _ensure_reranker_with_retry(self):
        """Retry-wrapped cross-encoder reranker initialization."""
        try:
            from app.services.retrieval.cross_encoder_reranker import get_reranker
            self.reranker = get_reranker()
            if self.reranker.is_available:
                logger.info("cross_encoder_reranker_attached")
            else:
                logger.warning("cross_encoder_reranker_unavailable")
                self.reranker = None
        except Exception as exc:
            logger.warning("reranker_init_failed", error=str(exc))
            self.reranker = None
            raise  # re-raise so tenacity can retry

    async def _ensure_hyde(self):
        """Lazy-init HyDE expansion if enabled and not yet initialized."""
        if self._hyde is None and self.use_hyde:
            try:
                from app.services.retrieval.hyde import HyDEModule
                self._hyde = HyDEModule(embedder=self.embedder)
                logger.info("hyde_attached")
            except Exception as exc:
                logger.warning("hyde_init_failed", error=str(exc))
                self._hyde = None

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────

    def calculate_dynamic_weights(self, query: str) -> dict[str, float]:
        q = query.lower()
        # Entity-based, year-specific keyword queries
        if any(char.isdigit() for char in q) or any(w in q for w in ["địa điểm", "ai là", "tên gì", "ngày tháng", "năm nào", "khi nào", "bao nhiêu"]):
            return {"vector": 0.3, "bm25": 0.7}
        # Conceptual / Comparative query
        if any(w in q for w in ["so sánh", "tại sao", "khác nhau", "bài học"]):
            return {"vector": 0.8, "bm25": 0.2}
        # Default balanced configuration
        return {"vector": 0.5, "bm25": 0.5}

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        filters: dict | None = None,
        vector_weight: float = 1.0,
        bm25_weight: float = 1.0,
        skip_rerank: bool = False,
    ) -> list[dict[str, Any]]:
        """
        Perform two-stage hybrid search + cross-encoder reranking.

        Args:
            query: Search query string.
            top_k: Final number of results to return (after reranking).
            filters: Metadata filters (year_from, year_to, document_id).
            vector_weight: RRF weight multiplier for vector search.
            bm25_weight: RRF weight multiplier for BM25 search.
            skip_rerank: If True, skip cross-encoder reranking (for speed).

        Returns:
            List of result dicts sorted by rerank_score, each containing:
                chunk_id, document_id, document_title, source_url,
                section_title, content, score, vector_score, bm25_score,
                cross_encoder_score, rerank_score.
        """
        if top_k <= 0:
            return []

        from app.core.context import chunk_limit_var
        custom_chunk_limit = chunk_limit_var.get()
        if custom_chunk_limit is not None:
            effective_top_k = custom_chunk_limit
        else:
            effective_top_k = min(top_k, self.final_top_k)

        # ── Historical Query Expansion ──────────────────────────────
        from app.services.retrieval.historical_utils import expand_historical_query
        expanded_query = expand_historical_query(query)
        if expanded_query != query:
            logger.info("query_expanded_historically", original=query, expanded=expanded_query)

        # ── HyDE Expansion (optional) ──────────────────────────────
        hyde_info: dict | None = None
        if self.use_hyde:
            await self._ensure_hyde()
            if self._hyde is not None:
                try:
                    hyde_info = await self._hyde.expand_query(query, top_k=effective_top_k)
                    logger.info("hyde_generated", hyde_chars=len(hyde_info.get("hypothetical_document", "")))
                except Exception as exc:
                    logger.warning("hyde_expansion_failed", error=str(exc))

        logger.info(
            "hybrid_search_start",
            query=query[:50],
            top_k=effective_top_k,
            skip_rerank=skip_rerank,
            hyde_enabled=hyde_info is not None,
        )

        # ── Stage 1: First-stage retrieval ─────────────────────────
        vector_results, bm25_results = await self._first_stage(
            query=expanded_query,
            candidate_size=self.candidate_size,
            filters=filters,
            hyde_info=hyde_info,
        )

        # Calculate dynamic weights based on the original query
        dynamic_weights = self.calculate_dynamic_weights(query)
        effective_vector_weight = vector_weight * dynamic_weights["vector"]
        effective_bm25_weight = bm25_weight * dynamic_weights["bm25"]

        # ── Stage 2: RRF Fusion ───────────────────────────────────
        fused = self.fusion.fuse(
            vector_results=vector_results,
            bm25_results=bm25_results,
            boost_vector=effective_vector_weight,
            boost_bm25=effective_bm25_weight,
        )

        if not fused:
            logger.warning("hybrid_search_no_results", query=query[:30])
            return []

        # ── Stage 3: Cross-encoder Reranking ──────────────────────
        if skip_rerank:
            candidates = fused[:effective_top_k]
            for item in candidates:
                item["cross_encoder_score"] = 0.0
                item["rerank_score"] = item.get("rrf_score", item.get("score", 0))
            results = candidates
        else:
            await self._ensure_reranker()
            if self.reranker is not None:
                candidates = fused  # give reranker full fused list to pick from
                reranked = self.reranker.rerank(
                    query=expanded_query,
                    candidates=candidates,
                    top_k=effective_top_k,
                )
                results = reranked
            else:
                # No reranker: use fusion scores as final scores
                for item in fused[:effective_top_k]:
                    item["cross_encoder_score"] = 0.0
                    item["rerank_score"] = item.get("rrf_score", item.get("score", 0))
                results = fused[:effective_top_k]

        # ── Stage 4: Metadata-Aware Boosting ────────────────────────
        from app.services.retrieval.query_metadata_extractor import extract_query_metadata
        query_meta = await extract_query_metadata(query)
        boost_dynasty = query_meta.get("dynasty")
        
        if boost_dynasty:
            logger.info("applying_metadata_boost", dynasty=boost_dynasty)
            for item in results:
                payload = item.get("payload") or {}
                chunk_dynasty = item.get("dynasty") or payload.get("dynasty")
                if chunk_dynasty == boost_dynasty:
                    boost_factor = 1.20
                    item["rerank_score"] = item.get("rerank_score", 0) * boost_factor
                    if "score" in item:
                        item["score"] = item["score"] * boost_factor
                    if "rrf_score" in item:
                        item["rrf_score"] = item["rrf_score"] * boost_factor

            results = sorted(results, key=lambda x: x.get("rerank_score", 0), reverse=True)

        # ── Stage 5: Normalize to standard output format ───────────
        return self._normalize(results)

    async def search_by_year_range(
        self,
        query: str,
        year_from: int,
        year_to: int,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search with year range filter."""
        return await self.hybrid_search(
            query=query,
            top_k=top_k,
            filters={"year_from": year_from, "year_to": year_to},
        )

    async def search_by_document(
        self,
        query: str,
        document_id: str,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Search within a specific document."""
        return await self.hybrid_search(
            query=query,
            top_k=top_k,
            filters={"document_id": document_id},
        )

    # ──────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────

    async def _first_stage(
        self,
        query: str,
        candidate_size: int,
        filters: dict | None,
        hyde_info: dict | None = None,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Run vector and BM25 searches depending on rag_mode."""
        from app.core.context import rag_mode_var
        mode = rag_mode_var.get()

        vector_results, bm25_results = [], []

        if mode == "keyword":
            bm25_results = await self._bm25_search(query, candidate_size, filters)
        elif mode == "vector":
            # Decide which vector to use: HyDE > original
            if hyde_info and hyde_info.get("hyde_vector"):
                query_vector = hyde_info["hyde_vector"]
                logger.info("using_hyde_vector", hyde_doc=hyde_info["hypothetical_document"][:80])
            else:
                query_embedding = await self.embedder.embed_async([query])
                query_vector = query_embedding[0].tolist() if len(query_embedding) > 0 else []
            vector_results = await self._vector_search(query_vector, candidate_size, filters)
        else:  # hybrid or default/None
            # Decide which vector to use: HyDE > original
            if hyde_info and hyde_info.get("hyde_vector"):
                query_vector = hyde_info["hyde_vector"]
                logger.info("using_hyde_vector", hyde_doc=hyde_info["hypothetical_document"][:80])
            else:
                query_embedding = await self.embedder.embed_async([query])
                query_vector = query_embedding[0].tolist() if len(query_embedding) > 0 else []

            # Run vector + BM25 in parallel
            vec_task = self._vector_search(query_vector, candidate_size, filters)
            bm25_task = self._bm25_search(query, candidate_size, filters)
            vector_results, bm25_results = await asyncio.gather(vec_task, bm25_task)

        logger.info(
            "first_stage_done",
            rag_mode=mode,
            vector_hits=len(vector_results),
            bm25_hits=len(bm25_results),
            hyde_used=hyde_info is not None,
        )
        return vector_results, bm25_results

    async def _vector_search(
        self,
        query_vector: list[float],
        top_k: int,
        filters: dict | None,
    ) -> list[dict[str, Any]]:
        """Query Qdrant vector search."""
        try:
            return await self.vector_search.search(
                query_vector=query_vector,
                top_k=top_k,
                filters=filters,
            )
        except Exception as exc:
            logger.error("vector_search_failed", error=str(exc))
            return []

    async def _bm25_search(
        self,
        query: str,
        top_k: int,
        filters: dict | None,
    ) -> list[dict[str, Any]]:
        """Query Meilisearch with in-memory fallback."""
        await self._ensure_meili_bm25()

        # Try Meilisearch first
        if self.meili_bm25 is not None:
            try:
                return await self.meili_bm25.search(
                    query=query,
                    top_k=top_k,
                    filters=filters,
                )
            except Exception as exc:
                logger.warning("meili_bm25_search_failed", error=str(exc))

        # Fall back to in-memory BM25 index
        try:
            from app.services.retrieval.bm25_index import get_bm25_index
            index = get_bm25_index()
            if index is not None:
                return index.search(query, top_k=top_k)
        except Exception as exc:
            logger.warning("inmemory_bm25_fallback_failed", error=str(exc))

        return []

    def _normalize(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert internal result format to the standard API format."""
        normalized = []
        for item in results:
            payload = item.get("payload") or {}
            normalized.append({
                "chunk_id":           item.get("id") or payload.get("chunk_id") or "",
                "document_id":        item.get("document_id") or payload.get("document_id") or "",
                "document_title":     item.get("document_title") or payload.get("document_title") or "Unknown",
                "source_url":         item.get("source_url") or payload.get("source_url"),
                "section_title":      item.get("section_title") or payload.get("section_title"),
                "content":            item.get("content") or payload.get("content") or "",
                "score":             item.get("rerank_score", item.get("rrf_score", item.get("score", 0))),
                "vector_score":      item.get("vector_score", 0),
                "bm25_score":        item.get("bm25_score", 0),
                "cross_encoder_score": item.get("cross_encoder_score", 0),
                "rerank_score":       item.get("rerank_score", 0),
                "dynasty":            item.get("dynasty") or payload.get("dynasty"),
                "geographical_region": item.get("geographical_region") or payload.get("geographical_region"),
                "highlight":          item.get("highlight"),
            })
        return normalized

