"""Lightweight reranking utilities."""

import re
from typing import Any


class LexicalReranker:
    """Rerank chunks by token overlap, source quality, and original score."""

    def rerank(self, query: str, chunks: list[dict[str, Any]], top_k: int = 8) -> list[dict[str, Any]]:
        query_terms = self._tokenize(query)
        if not query_terms:
            return chunks[:top_k]

        scored = []
        for chunk in chunks:
            content_terms = self._tokenize(chunk.get("content", ""))
            overlap = len(query_terms & content_terms) / max(len(query_terms), 1)
            source_score = float(chunk.get("score") or 0.0)
            rerank_score = (overlap * 0.7) + (source_score * 0.3)
            enriched = {**chunk, "rerank_score": rerank_score}
            scored.append(enriched)

        return sorted(scored, key=lambda item: item["rerank_score"], reverse=True)[:top_k]

    def _tokenize(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"\w+", text.lower())
            if len(token) >= 2
        }
