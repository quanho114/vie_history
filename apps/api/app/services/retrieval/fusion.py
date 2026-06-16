"""Hybrid search fusion."""

from typing import Any

import numpy as np

from app.core.logging import get_logger

logger = get_logger("fusion")


class FusionSearch:
    """
    Hybrid search using Reciprocal Rank Fusion (RRF).

    Combines vector search and BM25 results using RRF formula:
    RRF(d) = sum(1 / (k + rank(d)))

    Where k is a constant (typically 60).
    """

    def __init__(self, rrf_k: int = 60):
        self.rrf_k = rrf_k

    def fuse(
        self,
        vector_results: list[dict[str, Any]],
        bm25_results: list[dict[str, Any]],
        boost_vector: float = 1.0,
        boost_bm25: float = 1.0,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fuse results from multiple retrieval methods.

        Args:
            vector_results: Results from vector search
            bm25_results: Results from BM25 search
            boost_vector: Weight multiplier for vector scores
            boost_bm25: Weight multiplier for BM25 scores

        Returns:
            Fused results sorted by RRF score
        """
        scores: dict[str, dict[str, Any]] = {}

        # Add vector results
        for i, result in enumerate(vector_results):
            doc_id = result.get("id", f"vec_{i}")
            rrf_score = 1.0 / (self.rrf_k + i + 1)
            weighted_score = rrf_score * boost_vector

            scores[doc_id] = {
                **result,
                "id": doc_id,
                "rrf_score": weighted_score,
                "vector_rank": i + 1,
                "vector_score": result.get("score", 0),
                "payload": result.get("payload", {}),
                "content": result.get("content", ""),
            }

        # Add BM25 results
        for i, result in enumerate(bm25_results):
            doc_id = result.get("id", f"bm25_{i}")
            rrf_score = 1.0 / (self.rrf_k + i + 1)
            weighted_score = rrf_score * boost_bm25

            if doc_id in scores:
                scores[doc_id]["rrf_score"] += weighted_score
                scores[doc_id]["bm25_rank"] = i + 1
                scores[doc_id]["bm25_score"] = result.get("score", 0)
                # Merge BM25 fields that might not be in vector results
                for k, v in result.items():
                    if k not in scores[doc_id] or scores[doc_id][k] is None:
                        scores[doc_id][k] = v
            else:
                scores[doc_id] = {
                    **result,
                    "id": doc_id,
                    "rrf_score": weighted_score,
                    "bm25_rank": i + 1,
                    "bm25_score": result.get("score", 0),
                    "vector_rank": None,
                    "vector_score": 0,
                    "payload": {},
                    "content": result.get("content", ""),
                }

        # Sort by RRF score
        fused = sorted(
            scores.values(),
            key=lambda x: x["rrf_score"],
            reverse=True,
        )

        logger.info(
            "fusion_complete",
            vector_results=len(vector_results),
            bm25_results=len(bm25_results),
            fused_results=len(fused),
        )

        return fused[:top_k] if top_k is not None else fused

    def fuse_with_metadata(
        self,
        results: list[dict[str, Any]],
        metadata_boost: dict[str, float] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Fuse results with metadata-based boosting.

        Args:
            results: List of results
            metadata_boost: Dict of field -> boost multiplier

        Returns:
            Boosted and sorted results
        """
        if not metadata_boost:
            return results

        boosted = []
        for result in results:
            score = result.get("rrf_score", result.get("score", 0))
            payload = result.get("payload", {})

            # Apply metadata boosts
            for field, boost in metadata_boost.items():
                if field in payload:
                    score *= boost

            boosted.append({**result, "boosted_score": score})

        return sorted(boosted, key=lambda x: x["boosted_score"], reverse=True)
