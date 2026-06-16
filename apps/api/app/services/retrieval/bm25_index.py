"""Persistent BM25 index manager with Vietnamese tokenization support."""

from __future__ import annotations

import re
from typing import Any

from rank_bm25 import BM25Okapi
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger

logger = get_logger("bm25_index")


class VietnameseTokenizer:
    """
    Word-level tokenizer for Vietnamese text.

    Uses pyvi for proper word segmentation when available,
    falls back to a reasonable heuristic-based approach otherwise.
    """

    def __init__(self) -> None:
        self._pyvi_available = False
        try:
            from pyvi import ViTokenizer

            self._tokenizer = ViTokenizer
            self._pyvi_available = True
        except ImportError:
            self._tokenizer = None
            # Common Vietnamese stopwords to filter
            self._stopwords = {
                "và", "của", "là", "có", "được", "trong", "cho", "với",
                "để", "này", "đã", "không", "các", "những", "một", "về",
                "cũng", "ra", "hay", "tại", "sau", "trên", "từ", "bởi",
                "theo", "khi", "năm", "năm", "sự", "như", "vào", "hoặc",
                "nên", "đến", "do", "còn", "đó", "mà", "thì", "lại",
                "đều", "đang", "qua", "hơn", "khoảng", "ngay",
            }

    @property
    def available(self) -> bool:
        return self._pyvi_available

    def tokenize(self, text: str) -> list[str]:
        """Tokenize Vietnamese text into word-level tokens."""
        if not text:
            return []

        if self._pyvi_available:
            try:
                # pyvi returns e.g. "Hồ_Chí_Minh" for names
                tokenized = self._tokenizer.tokenize(text)
                # Split on underscore and whitespace, lowercase, filter short
                tokens = []
                for part in tokenized.split():
                    tokens.extend(t.lower() for t in re.split(r"_|\s+", part) if t)
                return [t for t in tokens if len(t) > 1]
            except Exception:
                pass

        # Fallback: simple character-aware tokenization
        # Remove punctuation, split on whitespace, filter tokens
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = []
        for token in cleaned.split():
            if len(token) > 1 and token not in self._stopwords:
                tokens.append(token)
        return tokens


class BM25Index:
    """
    In-memory BM25 index built from document chunks.

    The index is populated once at startup and updated incrementally
    when new chunks are ingested.
    """

    def __init__(self, tokenizer: VietnameseTokenizer | None = None) -> None:
        self._tokenizer = tokenizer or VietnameseTokenizer()
        self._corpus: list[str] = []
        self._corpus_ids: list[str] = []
        self._tokenized: list[list[str]] = []
        self._bm25: BM25Okapi | None = None
        # Maps chunk_id -> position in _corpus for O(1) updates
        self._id_to_idx: dict[str, int] = {}

    @property
    def size(self) -> int:
        return len(self._corpus)

    def index_chunks(self, chunks: list[dict[str, Any]]) -> None:
        """Build index from scratch with a list of chunks."""
        self._corpus = []
        self._corpus_ids = []
        self._tokenized = []
        self._id_to_idx.clear()

        for chunk in chunks:
            cid = str(chunk.get("id", ""))
            content = chunk.get("content", "")
            if not cid or not content:
                continue
            tokens = self._tokenizer.tokenize(content)
            self._corpus.append(content)
            self._corpus_ids.append(cid)
            self._tokenized.append(tokens)
            self._id_to_idx[cid] = len(self._corpus_ids) - 1

        if self._tokenized:
            self._bm25 = BM25Okapi(self._tokenized)
            logger.info(
                "bm25_index_built",
                num_chunks=len(self._corpus),
                pyvi_available=self._tokenizer.available,
            )

    def add_chunk(self, chunk: dict[str, Any]) -> None:
        """Incrementally add a single chunk to the index."""
        cid = str(chunk.get("id", ""))
        content = chunk.get("content", "")
        if not cid or not content or cid in self._id_to_idx:
            return

        tokens = self._tokenizer.tokenize(content)
        idx = len(self._corpus_ids)
        self._corpus.append(content)
        self._corpus_ids.append(cid)
        self._tokenized.append(tokens)
        self._id_to_idx[cid] = idx

        if self._bm25 is None:
            self._bm25 = BM25Okapi(self._tokenized)
        else:
            self._bm25.add_tokens(tokens)
        logger.debug("bm25_chunk_added", chunk_id=cid)

    def add_chunks(self, chunks: list[dict[str, Any]]) -> None:
        """Incrementally add multiple chunks without full rebuild."""
        for chunk in chunks:
            self.add_chunk(chunk)

    def remove_chunk(self, chunk_id: str) -> None:
        """Remove a chunk from the index."""
        if chunk_id not in self._id_to_idx:
            return
        idx = self._id_to_idx.pop(chunk_id)
        self._corpus.pop(idx)
        self._corpus_ids.pop(idx)
        self._tokenized.pop(idx)
        # Rebuild delta — acceptable for small removals
        self._bm25 = BM25Okapi(self._tokenized) if self._tokenized else None
        for cid, i in list(self._id_to_idx.items()):
            if i > idx:
                self._id_to_idx[cid] = i - 1
        logger.debug("bm25_chunk_removed", chunk_id=chunk_id)

    def search(self, query: str, top_k: int = 20) -> list[dict[str, Any]]:
        """Score all corpus docs against query, return top-k results."""
        if self._bm25 is None or not self._corpus:
            return []

        tokenized_query = self._tokenizer.tokenize(query)
        if not tokenized_query:
            return []

        scores = self._bm25.get_scores(tokenized_query)
        indexed = sorted(
            enumerate(scores),
            key=lambda x: x[1],
            reverse=True,
        )[:top_k]

        results = []
        for idx, score in indexed:
            if score > 0:
                results.append({
                    "id": self._corpus_ids[idx],
                    "score": float(score),
                    "content": self._corpus[idx],
                })
        return results


# Global index instance — populated once at startup
bm25_index: BM25Index | None = None


async def build_bm25_index(db: AsyncSession) -> BM25Index:
    """
    Load all indexed chunks from the database and build the BM25 index.

    Called once at application startup from the lifespan handler.
    """
    global bm25_index

    index = BM25Index()
    try:
        result = await db.execute(
            select(
                text("id::text"),
                text("content"),
            )
            .select_from(text("document_chunks"))
            .where(text("content IS NOT NULL AND content != ''"))
        )
        rows = result.fetchall()
        chunks = [{"id": row[0], "content": row[1]} for row in rows]
        index.index_chunks(chunks)
        bm25_index = index
        logger.info("bm25_startup_complete", total_chunks=len(chunks))
    except Exception as exc:
        logger.error("bm25_startup_failed", error=str(exc))

    return index


def get_bm25_index() -> BM25Index | None:
    """Return the global BM25 index, if initialized."""
    return bm25_index
