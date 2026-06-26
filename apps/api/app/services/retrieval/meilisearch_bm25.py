"""Meilisearch-backed persistent search replacing Elasticsearch.

Meilisearch provides:
- Very lightweight footprint compared to Elasticsearch.
- Persistence across restarts.
- Incremental updates (add/remove documents without full rebuild).
- Native fast fuzzy search, synonyms, and filter configurations.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from meilisearch_python_sdk import AsyncClient
from app.core.config import settings
from app.core.logging import get_logger

# Monkeypatch meilisearch-python-sdk to support older Meilisearch servers (v1.6.2)
try:
    import meilisearch_python_sdk.index as sdk_index
    search_globals = sdk_index.AsyncIndex.search.__globals__
    if 'process_search_parameters' in search_globals:
        original_process = search_globals['process_search_parameters']
        def patched_process(*args, **kwargs):
            body = original_process(*args, **kwargs)
            if "rankingScoreThreshold" in body and body["rankingScoreThreshold"] is None:
                del body["rankingScoreThreshold"]
            return body
        search_globals['process_search_parameters'] = patched_process
except Exception:
    pass

logger = get_logger("meilisearch_bm25")

INDEX_NAME = "historiai_chunks"

_DEFAULT_SYNONYMS = [
    "cmt8, cach mang thang tam, cach mang thang 8, cach mang thang tam 1945",
    "dien bien phu, chien dich dien bien phu, tran dien bien phu",
    "viet minh, muc vu, chinh phu ho chi minh, nuoc vn dan chu cong hoa",
    "hiip dong paris, hiep dong paris 1973, hieu uc paris",
    "vietnam, nuoc viet nam, viet-nam",
]


class MeilisearchBM25:
    """
    Persistent search backed by Meilisearch.

    Manages the lifecycle of the Meilisearch index and provides
    fast lexical search.
    """

    def __init__(
        self,
        url: str | None = None,
        index_name: str = INDEX_NAME,
        api_key: str | None = None,
    ):
        self.url = url or settings.MEILISEARCH_URL
        self.api_key = api_key or settings.MEILISEARCH_MASTER_KEY
        self.index_name = index_name
        self._client: AsyncClient | None = None
        self._initialized = False

    @property
    def client(self) -> AsyncClient:
        if self._client is None:
            self._client = AsyncClient(url=self.url, api_key=self.api_key)
        return self._client

    async def initialize(self) -> bool:
        """Ensure the Meilisearch index exists with correct mapping and settings."""
        if self._initialized:
            return True

        try:
            # Try to get the index, create it if not found
            try:
                await self.client.get_index(self.index_name)
                logger.info("meili_index_exists", index=self.index_name)
            except Exception:
                await self.client.create_index(self.index_name, primary_key="chunk_id")
                logger.info("meili_index_created", index=self.index_name)

            # Load and update synonyms, filterable attributes, and searchable attributes
            synonyms_list = await self._load_synonyms()
            synonyms_dict = {}
            for line in synonyms_list:
                tokens = [t.strip() for t in line.split(",") if t.strip()]
                for token in tokens:
                    synonyms_dict[token] = [t for t in tokens if t != token]

            index_client = self.client.index(self.index_name)
            await index_client.update_filterable_attributes(["document_id", "year"])
            await index_client.update_searchable_attributes(["document_title", "section_title", "content"])
            await index_client.update_synonyms(synonyms_dict)

            self._initialized = True
            return True
        except Exception as exc:
            logger.error("meili_init_failed", error=str(exc))
            return False

    async def _load_synonyms(self) -> list[str]:
        """Load historical synonyms from data file if present."""
        repo_root = Path(__file__).resolve().parents[4]
        synonyms_file = repo_root / "data" / "era_keywords.json"
        if not synonyms_file.exists():
            return _DEFAULT_SYNONYMS

        try:
            data = json.loads(synonyms_file.read_text(encoding="utf-8"))
            synonyms = []
            for event, keywords in data.items():
                if isinstance(keywords, list):
                    synonyms.append(", ".join(keywords))
            if synonyms:
                return synonyms
        except Exception as exc:
            logger.warning("meili_synonyms_load_failed", error=str(exc))
        return _DEFAULT_SYNONYMS

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict | None = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Search using Meilisearch.

        Args:
            query: Search query string.
            top_k: Number of results to return.
            filters: Optional metadata filters.
            min_score: Minimum matching score.

        Returns:
            List of result dicts sorted by score.
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Map filters to Meilisearch filter string
            filter_clauses = []
            if filters:
                if "document_id" in filters:
                    filter_clauses.append(f"document_id = '{filters['document_id']}'")
                if "year_from" in filters or "year_to" in filters:
                    year_from = filters.get("year_from", 0)
                    year_to = filters.get("year_to", 9999)
                    filter_clauses.append(f"year >= {year_from} AND year <= {year_to}")

            filter_str = " AND ".join(filter_clauses) if filter_clauses else None

            # Execute search
            index_client = self.client.index(self.index_name)
            response = await index_client.search(
                query,
                limit=top_k,
                filter=filter_str,
                attributes_to_highlight=["content"],
            )

            results = []
            for hit in response.hits:
                # Format highlights
                formatted = hit.get("_formatted", {})
                highlights = [formatted.get("content")] if formatted.get("content") else []

                results.append({
                    "id":             hit.get("chunk_id"),
                    "score":          float(hit.get("_rankingScore", 1.0)),
                    "content":        hit.get("content", ""),
                    "document_id":     hit.get("document_id"),
                    "document_title":  hit.get("document_title", "Unknown"),
                    "section_title":   hit.get("section_title"),
                    "source_url":      hit.get("source_url"),
                    "year":           hit.get("year"),
                    "quality_score":   hit.get("quality_score", 0),
                    "highlight":      highlights,
                })

            logger.info(
                "meili_search",
                query=query[:30],
                returned=len(results),
            )
            return results

        except Exception as exc:
            logger.error("meili_search_error", error=str(exc))
            return []

    async def index_chunk(self, chunk: dict[str, Any]) -> bool:
        """Index or update a single document chunk."""
        if not self._initialized:
            await self.initialize()

        try:
            chunk_id = str(chunk.get("id") or chunk.get("chunk_id", ""))
            body = {
                "chunk_id":        chunk_id,
                "document_id":     chunk.get("document_id", ""),
                "document_title":  chunk.get("document_title", ""),
                "section_title":   chunk.get("section_title"),
                "content":         chunk.get("content", ""),
                "year":            chunk.get("year"),
                "source_url":      chunk.get("source_url"),
                "quality_score":   chunk.get("quality_score", 0),
                "token_count":     chunk.get("token_count"),
                "indexed_at":      datetime.utcnow().isoformat(),
            }
            index_client = self.client.index(self.index_name)
            await index_client.add_documents([body])
            logger.debug("meili_chunk_indexed", chunk_id=chunk_id)
            return True
        except Exception as exc:
            logger.error("meili_index_chunk_error", chunk_id=chunk.get("id"), error=str(exc))
            return False

    async def index_chunks(self, chunks: list[dict[str, Any]]) -> int:
        """Bulk-index a list of document chunks."""
        if not self._initialized:
            await self.initialize()

        if not chunks:
            return 0

        try:
            documents = []
            for chunk in chunks:
                chunk_id = str(chunk.get("id") or chunk.get("chunk_id", ""))
                documents.append({
                    "chunk_id":        chunk_id,
                    "document_id":     chunk.get("document_id", ""),
                    "document_title":  chunk.get("document_title", ""),
                    "section_title":   chunk.get("section_title"),
                    "content":         chunk.get("content", ""),
                    "year":            chunk.get("year"),
                    "source_url":      chunk.get("source_url"),
                    "quality_score":   chunk.get("quality_score", 0),
                    "token_count":     chunk.get("token_count"),
                    "indexed_at":      datetime.utcnow().isoformat(),
                })

            index_client = self.client.index(self.index_name)
            await index_client.add_documents(documents)
            logger.info("meili_bulk_index_complete", count=len(documents))
            return len(documents)
        except Exception as exc:
            logger.error("meili_bulk_index_error", error=str(exc))
            return 0

    async def remove_chunk(self, chunk_id: str) -> bool:
        """Remove a chunk from the index by ID."""
        try:
            index_client = self.client.index(self.index_name)
            await index_client.delete_document(chunk_id)
            logger.debug("meili_chunk_removed", chunk_id=chunk_id)
            return True
        except Exception as exc:
            logger.error("meili_remove_chunk_error", chunk_id=chunk_id, error=str(exc))
            return False

    async def remove_by_document_id(self, document_id: str) -> int:
        """Remove all chunks associated with a document_id."""
        if not self._initialized:
            await self.initialize()
        try:
            index_client = self.client.index(self.index_name)
            await index_client.delete_documents_by_filter(f"document_id = '{document_id}'")
            logger.info("meili_document_chunks_removed", document_id=document_id)
            return 1
        except Exception as exc:
            logger.error("meili_remove_by_document_id_error", document_id=document_id, error=str(exc))
            return 0

    async def refresh_index(self) -> None:
        """Meilisearch handles updates asynchronously, no-op for refresh."""
        pass

    async def get_index_stats(self) -> dict[str, Any]:
        """Return index statistics."""
        try:
            index_client = self.client.index(self.index_name)
            stats = await index_client.get_stats()
            return {
                "doc_count":    stats.number_of_documents,
                "size_bytes":   0,  # Meilisearch does not expose DB size via stats
                "index_name":   self.index_name,
            }
        except Exception as exc:
            logger.warning("meili_stats_error", error=str(exc))
            return {}

    async def close(self) -> None:
        """Close the Meilisearch client."""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._initialized = False
            logger.info("meili_client_closed")


# === Module-level global instance ===

_meili_bm25: MeilisearchBM25 | None = None


async def get_meilisearch_bm25() -> MeilisearchBM25:
    """Return the shared MeilisearchBM25 instance, initializing if needed."""
    global _meili_bm25
    if _meili_bm25 is None:
        _meili_bm25 = MeilisearchBM25()
    await _meili_bm25.initialize()
    return _meili_bm25


async def close_meilisearch_bm25() -> None:
    """Close the global Meilisearch client."""
    global _meili_bm25
    if _meili_bm25:
        await _meili_bm25.close()
        _meili_bm25 = None
