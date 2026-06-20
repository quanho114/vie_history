"""Cross-encoder reranker for precision-boosted retrieval.

Cross-encoder reranking is the second-stage refinement step after hybrid
search (vector + BM25 fusion). It takes a larger candidate set from
first-stage retrieval and re-scores every (query, document) pair using
a pretrained cross-encoder model, dramatically improving precision for
the final top-K results.

Why cross-encoder > bi-encoder for reranking:
- Bi-encoder: encodes query and document independently, then compares
  vectors. Fast but loses fine-grained relevance signal.
- Cross-encoder: encodes query+document jointly, capturing direct
  term interactions and contextual relevance. Slower but far more
  accurate for reranking.

Design decisions:
- Lazy-loads the model on first use to keep startup time low.
- Runs inference in a thread pool to avoid blocking the async event loop.
- Falls back to LexicalReranker if the model is unavailable.
- Batch-encodes all candidates in a single forward pass for efficiency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from app.core.logging import get_logger

if TYPE_CHECKING:
    from sentence_transformers import CrossEncoder

logger = get_logger("cross_encoder_reranker")

# Supported multilingual cross-encoder models for Vietnamese.
# These models are trained on sentence-level relevance data.
_CROSS_ENCODER_POOL = [
    # BGE Reranker Large (state-of-the-art cross-encoder for Vietnamese/multilingual)
    "BAAI/bge-reranker-large",
    #ms-marco = trained on Bing query-document relevance pairs, multilingual
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
    #ms-marco multilingual — better for non-English queries
    "cross-encoder/ms-marco-multilingual-MiniLM-L6-v2",
    #ms-marco with deeper model
    "cross-encoder/ms-marco-MiniLM-L-12-v2",
]

# Default candidate pool size before reranking.
# Retrieve more than final K to give the reranker room to promote
# truly relevant docs that might rank low in first-stage retrieval.
DEFAULT_CANDIDATE_SIZE = 20


class CrossEncoderReranker:
    """
    Second-stage cross-encoder reranker.

    Reranks first-stage candidates by scoring (query, document) pairs
    with a pretrained cross-encoder. Returns top-K reranked results.

    Example flow:
        query = "Chiến dịch Điện Biên Phủ"
        candidates = fusion.fuse(vector_results, bm25_results)  # top-20
        reranked = reranker.rerank(query, candidates, top_k=5)
    """

    def __init__(
        self,
        model_name: str | None = None,
        max_length: int = 512,
        candidate_size: int = DEFAULT_CANDIDATE_SIZE,
        device: str = "cpu",
        batch_size: int = 8,
        blend_weight: float = 0.7,
    ):
        self.model_name = model_name or _CROSS_ENCODER_POOL[0]
        self.max_length = max_length
        self.candidate_size = candidate_size
        self.device = device
        self.batch_size = batch_size
        self.blend_weight = blend_weight
        self._model: CrossEncoder | None = None
        self._loaded = False
        self._available: bool | None = None

    def _ensure_model(self) -> bool:
        """Lazy-load the cross-encoder model. Returns True if loaded."""
        if self._available is not None:
            return self._available and self._model is not None

        if self._loaded:
            return self._model is not None

        self._loaded = True
        try:
            from sentence_transformers import CrossEncoder as _CE
            self._model = _CE(
                self.model_name,
                max_length=self.max_length,
                device=self.device,
            )
            logger.info(
                "cross_encoder_loaded",
                model=self.model_name,
                device=self.device,
            )
            return True
        except Exception as exc:
            logger.warning(
                "cross_encoder_load_failed",
                model=self.model_name,
                error=str(exc),
            )
            return False

    @property
    def is_available(self) -> bool:
        """Check if the reranker model is loaded and usable."""
        if self._available is not None:
            return self._available and self._model is not None
        return self._model is not None

    def rerank(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Rerank candidate documents by cross-encoder relevance score.

        Args:
            query: The search query.
            candidates: List of candidate dicts from first-stage retrieval.
                Each dict must contain at least 'content' (document text).
                Optional fields: 'id', 'score', 'payload'.
            top_k: Number of top results to return after reranking.

        Returns:
            List of reranked candidate dicts, each augmented with
            'cross_encoder_score' and 'rerank_score' (final score).
        """
        if not candidates:
            return []

        # Trim to candidate pool size
        pool = candidates[: self.candidate_size]

        # Fall back to lexical reranker if model unavailable
        if not self._ensure_model():
            return self._fallback_lexical(query, pool, top_k)

        try:
            # Build (query, text) pairs for all candidates
            texts = [c.get("content", c.get("payload", {}).get("content", "")) for c in pool]
            pairs = [[query, text] for text in texts]

            # Run cross-encoder scoring in batch — use ThreadPoolExecutor instead of
            # creating a new event loop per call (avoids event loop leak).
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                scores = list(executor.map(lambda p: self._score_batch_sync(p), [pairs]))[0]

            # Augment candidates with cross-encoder scores
            reranked = []
            for i, candidate in enumerate(pool):
                ce_score = float(scores[i]) if i < len(scores) else 0.0
                first_stage_score = float(candidate.get("rrf_score", candidate.get("score", 0)))

                # Blend cross-encoder score with first-stage score (weighted average).
                # Cross-encoder (precision signal) gets 70%, first-stage (recall signal) gets 30%.
                blended = (ce_score * self.blend_weight) + (
                    first_stage_score * (1 - self.blend_weight)
                )

                enriched = {
                    **candidate,
                    "cross_encoder_score": ce_score,
                    "rerank_score": blended,
                }
                reranked.append(enriched)

            # Sort by rerank_score descending
            reranked.sort(key=lambda x: x["rerank_score"], reverse=True)

            result = reranked[:top_k]
            logger.info(
                "rerank_complete",
                query=query[:30],
                candidates=len(pool),
                top_k=len(result),
            )
            return result

        except Exception as exc:
            logger.error("rerank_error", error=str(exc))
            return self._fallback_lexical(query, pool, top_k)

    async def _score_batch_async(
        self,
        pairs: list[list[str]],
    ) -> list[float]:
        """Run cross-encoder scoring in a thread pool (non-blocking)."""
        import asyncio
        loop = asyncio.get_running_loop()
        scores = await loop.run_in_executor(
            None,
            self._score_batch_sync,
            pairs,
        )
        return scores

    def _score_batch_sync(self, pairs: list[list[str]]) -> list[float]:
        """Synchronous batch scoring — call from thread pool."""
        if not self._model:
            return []
        if callable(self._model):
            return list(self._model(pairs))
        return self._model.predict(pairs, show_progress_bar=False).tolist()

    def _fallback_lexical(
        self,
        query: str,
        candidates: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        """Fallback when cross-encoder is unavailable."""
        from app.retrieval.reranker import LexicalReranker
        reranker = LexicalReranker()
        results = reranker.rerank(query, candidates, top_k=top_k)
        for r in results:
            r["cross_encoder_score"] = 0.0
            r["rerank_score"] = r.get("rerank_score", r.get("score", 0))
        logger.info("rerank_fallback_lexical", top_k=top_k)
        return results


# === Module-level convenience functions ===

_reranker_instance: CrossEncoderReranker | None = None


def get_reranker() -> CrossEncoderReranker:
    """Return a shared CrossEncoderReranker instance."""
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = CrossEncoderReranker()
    return _reranker_instance
