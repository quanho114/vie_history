"""BM25 lexical search service."""

import re
from typing import Any

from rank_bm25 import BM25Okapi

from app.core.logging import get_logger

logger = get_logger("bm25_search")


class BM25Search:
    """
    BM25 lexical search for Vietnamese text.
    Uses whitespace tokenization with fallback.
    """

    def __init__(
        self,
        k1: float = 1.5,
        b: float = 0.75,
        top_k: int = 20,
    ):
        self.k1 = k1
        self.b = b
        self.top_k = top_k
        self._corpus: list[str] = []
        self._corpus_ids: list[str] = []
        self._tokenized_corpus: list[list[str]] = []
        self._bm25: BM25Okapi | None = None

    def _tokenize(self, text: str) -> list[str]:
        """
        Tokenize text for BM25.
        Basic whitespace + lowercase for Vietnamese.
        """
        # Lowercase and split on whitespace
        tokens = re.findall(r"\b\w+\b", text.lower())
        return tokens

    def index(self, chunks: list[dict[str, Any]]) -> None:
        """
        Build BM25 index from chunks.

        Args:
            chunks: List of chunk dicts with 'id' and 'content' keys
        """
        self._corpus = []
        self._corpus_ids = []
        self._tokenized_corpus = []

        for chunk in chunks:
            content = chunk.get("content", "")
            chunk_id = chunk.get("id", "")

            if content and chunk_id:
                self._corpus.append(content)
                self._corpus_ids.append(chunk_id)
                self._tokenized_corpus.append(self._tokenize(content))

        if self._tokenized_corpus:
            self._bm25 = BM25Okapi(
                self._tokenized_corpus,
                k1=self.k1,
                b=self.b,
            )
            logger.info("bm25_indexed", num_chunks=len(self._corpus))

    def search(self, query: str, top_k: int | None = None) -> list[dict[str, Any]]:
        """
        Search using BM25.

        Args:
            query: Search query
            top_k: Number of results (default: self.top_k)

        Returns:
            List of results with scores
        """
        if self._bm25 is None or not self._corpus:
            return []

        k = top_k or self.top_k
        tokenized_query = self._tokenize(query)
        scores = self._bm25.get_scores(tokenized_query)

        # Get top-k indices
        top_indices = sorted(
            range(len(scores)),
            key=lambda i: scores[i],
            reverse=True,
        )[:k]

        results = []
        for idx in top_indices:
            if scores[idx] > 0:
                results.append({
                    "id": self._corpus_ids[idx],
                    "score": float(scores[idx]),
                    "content": self._corpus[idx],
                })

        return results

    def clear(self) -> None:
        """Clear the index."""
        self._corpus = []
        self._corpus_ids = []
        self._tokenized_corpus = []
        self._bm25 = None
