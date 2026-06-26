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
        device: str | None = None,
        batch_size: int = 8,
        blend_weight: float = 0.7,
    ):
        from app.core.config import settings
        self.model_name = model_name or settings.VIETNAMESE_RERANKER_MODEL or _CROSS_ENCODER_POOL[0]
        self.max_length = max_length
        self.candidate_size = candidate_size
        self.batch_size = batch_size
        self.blend_weight = blend_weight
        self._model: CrossEncoder | None = None
        self._loaded = False
        self._available: bool | None = None

        if device is None:
            try:
                import torch
                if torch.cuda.is_available():
                    self.device = "cuda"
                elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    self.device = "mps"
                else:
                    self.device = "cpu"
            except ImportError:
                self.device = "cpu"
        else:
            self.device = device

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
                local_files_only=True,
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
            # Try cached fallback model
            fallback_model = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli"
            if self.model_name != fallback_model:
                try:
                    logger.info("attempting_fallback_cached_model", model=fallback_model)
                    from sentence_transformers import CrossEncoder as _CE
                    self._model = _CE(
                        fallback_model,
                        max_length=self.max_length,
                        device=self.device,
                        local_files_only=True,
                    )
                    self.model_name = fallback_model
                    logger.info(
                        "cross_encoder_loaded_fallback",
                        model=fallback_model,
                        device=self.device,
                    )
                    return True
                except Exception as fallback_exc:
                    logger.warning(
                        "cross_encoder_fallback_failed",
                        model=fallback_model,
                        error=str(fallback_exc),
                    )
                    # Last resort: try online load of the originally configured model
                    try:
                        logger.info("attempting_online_download_of_configured_model", model=self.model_name)
                        from sentence_transformers import CrossEncoder as _CE
                        self._model = _CE(
                            self.model_name,
                            max_length=self.max_length,
                            device=self.device,
                        )
                        logger.info(
                            "cross_encoder_loaded_online",
                            model=self.model_name,
                            device=self.device,
                        )
                        return True
                    except Exception as online_exc:
                        logger.warning(
                            "cross_encoder_online_load_failed",
                            model=self.model_name,
                            error=str(online_exc),
                        )
            return False

    @property
    def is_available(self) -> bool:
        """Check if the reranker model is loaded and usable."""
        return self._ensure_model()

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

            # Run cross-encoder scoring directly on the current thread to avoid openmp/threading deadlocks
            scores = self._score_batch_sync(pairs)

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
            if "out of memory" in str(exc).lower():
                logger.warning("rerank_cuda_oom_falling_back_to_cpu")
                try:
                    import torch
                    torch.cuda.empty_cache()
                except Exception:
                    pass
                self.device = "cpu"
                self._model = None
                self._loaded = False
                if self._ensure_model():
                    try:
                        # Retry on CPU directly
                        texts = [c.get("content", c.get("payload", {}).get("content", "")) for c in pool]
                        pairs = [[query, text] for text in texts]
                        scores = self._score_batch_sync(pairs)
                        
                        reranked = []
                        for i, candidate in enumerate(pool):
                            ce_score = float(scores[i]) if i < len(scores) else 0.0
                            first_stage_score = float(candidate.get("rrf_score", candidate.get("score", 0)))
                            blended = (ce_score * self.blend_weight) + (
                                first_stage_score * (1 - self.blend_weight)
                            )
                            enriched = {
                                **candidate,
                                "cross_encoder_score": ce_score,
                                "rerank_score": blended,
                            }
                            reranked.append(enriched)
                        reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
                        result = reranked[:top_k]
                        logger.info(
                            "rerank_complete_on_cpu",
                            query=query[:30],
                            candidates=len(pool),
                            top_k=len(result),
                        )
                        return result
                    except Exception as cpu_exc:
                        logger.error("rerank_cpu_retry_failed", error=str(cpu_exc))
            
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
        
        # If it's the NLI fallback model, we need to format the pairs as:
        # [premise, hypothesis] where premise = chunk text, hypothesis = template
        is_nli = "mnli" in self.model_name.lower() or "xnli" in self.model_name.lower()
        
        nli_pairs = []
        if is_nli:
            for pair in pairs:
                query, text = pair[0], pair[1]
                # Format: [premise, hypothesis]
                # template: "Văn bản này trả lời cho câu hỏi: {query}"
                hyp = f"Văn bản này trả lời cho câu hỏi: {query}"
                nli_pairs.append([text, hyp])
            eval_pairs = nli_pairs
        else:
            eval_pairs = pairs

        if hasattr(self._model, "predict"):
            raw_scores = self._model.predict(eval_pairs, show_progress_bar=False)
        else:
            raw_scores = self._model(eval_pairs)

        # Convert to numpy array for operations
        import numpy as np
        raw_scores = np.array(raw_scores)

        # If it is NLI model (returning 3 classes), extract entailment probability
        if is_nli and len(raw_scores.shape) == 2 and raw_scores.shape[1] == 3:
            # Softmax over classes (dimension 1)
            exp_scores = np.exp(raw_scores - np.max(raw_scores, axis=-1, keepdims=True))
            probs = exp_scores / exp_scores.sum(axis=-1, keepdims=True)
            
            # Find entailment label index (usually 0)
            entailment_idx = 0
            try:
                if hasattr(self._model, "model") and hasattr(self._model.model, "config"):
                    label2id = getattr(self._model.model.config, "label2id", {})
                    entailment_idx = label2id.get("entailment", 0)
            except Exception:
                pass
            
            scores = probs[:, entailment_idx].tolist()
        else:
            if len(raw_scores.shape) > 1:
                scores = raw_scores.flatten().tolist()
            else:
                scores = raw_scores.tolist()

        return scores

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
