"""Elasticsearch-backed persistent BM25 search.

Elasticsearch replaces the in-memory rank_bm25 index to provide:
- Persistence across restarts (index survives process restarts).
- Incremental updates (add/remove documents without full rebuild).
- Horizontal scalability for large document collections.
- Full-text features: analyzers, synonyms, fuzzy matching, highlighting.
- Integration with the rest of the ELK stack for monitoring.

Vietnamese text processing:
- Uses the built-in 'vi' analyzer for proper tokenization.
- Custom synonyms list maps historical period names to modern variants.
- Handles special characters and diacritics.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx
from elasticsearch import AsyncElasticsearch

from app.core.config import settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger("elasticsearch_bm25")

INDEX_NAME = "historiai_chunks"

# Vietnamese historical synonyms — maps period names / aliases to canonical forms.
# Loaded lazily from a local JSON file on first index creation.
_DEFAULT_SYNONYMS = [
    "cmt8, cach mang thang tam, cach mang thang 8, cach mang thang tam 1945",
    "dien bien phu, chien dich dien bien phu, tran dien bien phu",
    "viet minh, muc vu, chinh phu ho chi minh, nuoc vn dan chu cong hoa",
    "hiip dong paris, hiep dong paris 1973, hieu uc paris",
    "vietnam, nuoc viet nam, viet-nam",
]

# Chunk document mapping for Elasticsearch.
# Controls which fields are indexed, analyzed, and stored.
CHUNK_MAPPING = {
    "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 0,
        "analysis": {
            "filter": {
                "vietnamese_stop": {
                    "type": "stop",
                    "stopwords": "_vietnamese_",
                },
            },
            "analyzer": {
                "vietnamese_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                        "vietnamese_stop",
                    ],
                },
                "vietnamese_search_analyzer": {
                    "type": "custom",
                    "tokenizer": "standard",
                    "filter": [
                        "lowercase",
                    ],
                },
            },
            "synonym": {
                "vietnamese_synonyms": {
                    "type": "synonym",
                    "synonyms": _DEFAULT_SYNONYMS,
                },
            },
        },
    },
    "mappings": {
        "properties": {
            "chunk_id":          {"type": "keyword"},
            "document_id":       {"type": "keyword"},
            "document_title":    {"type": "text", "analyzer": "vietnamese_analyzer", "fields": {"keyword": {"type": "keyword"}}},
            "section_title":     {"type": "text", "analyzer": "vietnamese_analyzer"},
            "content": {
                "type": "text",
                "analyzer": "vietnamese_analyzer",
                "search_analyzer": "vietnamese_search_analyzer",
                "term_vector": "with_positions_offsets",
            },
            "year":              {"type": "integer"},
            "year_range":        {"type": "keyword"},
            "source_url":        {"type": "keyword", "index": False},
            "quality_score":     {"type": "float"},
            "token_count":       {"type": "integer"},
            "indexed_at":        {"type": "date"},
        },
    },
}


class ElasticsearchBM25:
    """
    Persistent BM25 search backed by Elasticsearch.

    Manages the lifecycle of the Elasticsearch index and provides
    BM25-based lexical search with Vietnamese text analysis.

    Usage:
        es = ElasticsearchBM25()
        await es.initialize()           # ensure index exists
        results = await es.search("Hồ Chí Minh", top_k=10)
        await es.index_chunk(chunk_data)
        await es.remove_chunk("chunk-uuid")
        await es.close()
    """

    def __init__(
        self,
        url: str | None = None,
        index_name: str = INDEX_NAME,
        timeout: int = 30,
    ):
        self.url = url or settings.ELASTICSEARCH_URL
        self.index_name = index_name
        self.timeout = timeout
        self._client: AsyncElasticsearch | None = None
        self._initialized = False

    @property
    def client(self) -> AsyncElasticsearch:
        if self._client is None:
            self._client = AsyncElasticsearch(
                hosts=[self.url],
                request_timeout=self.timeout,
            )
        return self._client

    async def initialize(self) -> bool:
        """Ensure the Elasticsearch index exists with correct mapping."""
        if self._initialized:
            return True

        try:
            exists = await self.client.indices.exists(index=self.index_name)
            if not exists:
                synonyms = await self._load_synonyms()
                body = self._build_mapping(synonyms)
                await self.client.indices.create(index=self.index_name, body=body)
                logger.info("es_index_created", index=self.index_name)
            else:
                logger.info("es_index_exists", index=self.index_name)
            self._initialized = True
            return True
        except Exception as exc:
            logger.error("es_init_failed", error=str(exc))
            return False

    async def _load_synonyms(self) -> list[str]:
        """Load historical synonyms from data file if present."""
        repo_root = Path(__file__).resolve().parents[4]
        synonyms_file = repo_root / "data" / "era_keywords.json"
        if not synonyms_file.exists():
            return _DEFAULT_SYNONYMS

        try:
            data = json.loads(synonyms_file.read_text(encoding="utf-8"))
            # era_keywords.json has events mapped to keyword lists
            synonyms = []
            for event, keywords in data.items():
                if isinstance(keywords, list):
                    synonyms.append(", ".join(keywords))
            if synonyms:
                return synonyms
        except Exception as exc:
            logger.warning("es_synonyms_load_failed", error=str(exc))
        return _DEFAULT_SYNONYMS

    def _build_mapping(self, synonyms: list[str]) -> dict[str, Any]:
        """Build full Elasticsearch index body with synonyms injected."""
        body = json.loads(json.dumps(CHUNK_MAPPING))  # deep copy
        # Inject loaded synonyms into the mapping
        if "analysis" not in body["settings"]:
            body["settings"]["analysis"] = {}
        if "filter" not in body["settings"]["analysis"]:
            body["settings"]["analysis"]["filter"] = {}
        body["settings"]["analysis"]["filter"]["vietnamese_synonyms"] = {
            "type": "synonym",
            "synonyms": synonyms,
        }
        vi_analyzer = body["settings"]["analysis"]["analyzer"].get("vietnamese_analyzer", {})
        filters = vi_analyzer.get("filter", [])
        if "vietnamese_synonyms" not in filters:
            vi_analyzer["filter"] = filters + ["vietnamese_synonyms"]
        return body

    async def search(
        self,
        query: str,
        top_k: int = 10,
        filters: dict | None = None,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Search using Elasticsearch BM25 with Vietnamese analysis.

        Args:
            query: Search query string.
            top_k: Number of results to return.
            filters: Optional metadata filters.
                - year_from / year_to: integer year range
                - document_id: exact match on document
            min_score: Minimum BM25 score threshold.

        Returns:
            List of result dicts sorted by BM25 score.
        """
        if not self._initialized:
            await self.initialize()

        try:
            # Build Elasticsearch query
            es_query: dict[str, Any] = {"match": {"content": {"query": query}}}

            # Apply metadata filters
            must_clauses: list[dict[str, Any]] = [es_query]
            filter_clauses: list[dict[str, Any]] = []

            if filters:
                if "year_from" in filters or "year_to" in filters:
                    year_from = filters.get("year_from", 0)
                    year_to = filters.get("year_to", 9999)
                    filter_clauses.append({
                        "range": {"year": {"gte": year_from, "lte": year_to}}
                    })
                if "document_id" in filters:
                    filter_clauses.append({
                        "term": {"document_id": filters["document_id"]}
                    })

            body = {
                "query": {
                    "bool": {
                        "must": must_clauses,
                        "filter": filter_clauses,
                    }
                },
                "size": top_k,
                "min_score": min_score,
                "_source": True,
                "highlight": {
                    "fields": {
                        "content": {
                            "fragment_size": 200,
                            "number_of_fragments": 2,
                        }
                    }
                },
            }

            response = await self.client.search(index=self.index_name, body=body)
            hits = response.get("hits", {}).get("hits", [])

            results = []
            for hit in hits:
                source = hit.get("_source", {})
                results.append({
                    "id":           source.get("chunk_id"),
                    "score":        float(hit.get("_score", 0)),
                    "content":      source.get("content", ""),
                    "document_id":   source.get("document_id"),
                    "document_title": source.get("document_title", "Unknown"),
                    "section_title": source.get("section_title"),
                    "source_url":   source.get("source_url"),
                    "year":         source.get("year"),
                    "quality_score": source.get("quality_score", 0),
                    "highlight":    hit.get("highlight", {}).get("content", []),
                })

            logger.info(
                "es_search",
                query=query[:30],
                total=response.get("hits", {}).get("total", {}).get("value", 0),
                returned=len(results),
            )
            return results

        except Exception as exc:
            logger.error("es_search_error", error=str(exc))
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
                "year_range":      self._year_to_range(chunk.get("year")),
                "source_url":      chunk.get("source_url"),
                "quality_score":   chunk.get("quality_score", 0),
                "token_count":     chunk.get("token_count"),
                "indexed_at":      datetime.utcnow().isoformat(),
            }
            await self.client.index(
                index=self.index_name,
                id=chunk_id,
                document=body,
                refresh=True,
            )
            logger.debug("es_chunk_indexed", chunk_id=chunk_id)
            return True
        except Exception as exc:
            logger.error("es_index_chunk_error", chunk_id=chunk.get("id"), error=str(exc))
            return False

    async def index_chunks(self, chunks: list[dict[str, Any]]) -> int:
        """Bulk-index a list of document chunks."""
        if not self._initialized:
            await self.initialize()

        if not chunks:
            return 0

        try:
            operations = []
            for chunk in chunks:
                chunk_id = str(chunk.get("id") or chunk.get("chunk_id", ""))
                body = {
                    "chunk_id":        chunk_id,
                    "document_id":     chunk.get("document_id", ""),
                    "document_title":  chunk.get("document_title", ""),
                    "section_title":   chunk.get("section_title"),
                    "content":         chunk.get("content", ""),
                    "year":            chunk.get("year"),
                    "year_range":      self._year_to_range(chunk.get("year")),
                    "source_url":      chunk.get("source_url"),
                    "quality_score":   chunk.get("quality_score", 0),
                    "token_count":     chunk.get("token_count"),
                    "indexed_at":      datetime.utcnow().isoformat(),
                }
                operations.append({"index": {"_index": self.index_name, "_id": chunk_id}})
                operations.append(body)

            response = await self.client.bulk(operations=operations, refresh=False)
            # Count successes
            errors = [item for item in response.get("items", []) if item.get("index", {}).get("error")]
            indexed = len(chunks) - len(errors)
            if errors:
                first_error = errors[0]["index"]["error"]
                logger.warning("es_bulk_index_partial", indexed=indexed, failed=len(errors), first_error=str(first_error))
            else:
                logger.info("es_bulk_index_complete", indexed=indexed)
            return indexed
        except Exception as exc:
            logger.error("es_bulk_index_error", error=str(exc))
            return 0

    async def remove_chunk(self, chunk_id: str) -> bool:
        """Remove a chunk from the index by ID."""
        try:
            await self.client.delete(index=self.index_name, id=chunk_id, refresh=True)
            logger.debug("es_chunk_removed", chunk_id=chunk_id)
            return True
        except Exception as exc:
            logger.error("es_remove_chunk_error", chunk_id=chunk_id, error=str(exc))
            return False

    async def remove_by_document_id(self, document_id: str) -> int:
        """Remove all chunks associated with a document_id."""
        if not self._initialized:
            await self.initialize()
        try:
            body = {
                "query": {
                    "term": {
                        "document_id": document_id
                    }
                }
            }
            response = await self.client.delete_by_query(
                index=self.index_name,
                body=body,
                refresh=True
            )
            deleted = response.get("deleted", 0)
            logger.info("es_document_chunks_removed", document_id=document_id, count=deleted)
            return deleted
        except Exception as exc:
            logger.error("es_remove_by_document_id_error", document_id=document_id, error=str(exc))
            return 0

    async def refresh_index(self) -> None:
        """Force refresh the index to make recent updates searchable."""
        try:
            await self.client.indices.refresh(index=self.index_name)
        except Exception as exc:
            logger.warning("es_refresh_error", error=str(exc))

    async def get_index_stats(self) -> dict[str, Any]:
        """Return index statistics (doc count, size, etc.)."""
        try:
            stats = await self.client.indices.stats(index=self.index_name)
            total = stats.get("indices", {}).get(self.index_name, {})
            return {
                "doc_count":    total.get("primaries", {}).get("docs", {}).get("count", 0),
                "size_bytes":   total.get("primaries", {}).get("store", {}).get("size_in_bytes", 0),
                "index_name":   self.index_name,
            }
        except Exception as exc:
            logger.warning("es_stats_error", error=str(exc))
            return {}

    async def close(self) -> None:
        """Close the Elasticsearch client."""
        if self._client:
            await self._client.close()
            self._client = None
            self._initialized = False
            logger.info("es_client_closed")

    @staticmethod
    def _year_to_range(year: int | None) -> str | None:
        if year is None:
            return None
        # Map year to a decade range for faceted filtering
        decade = (year // 10) * 10
        return f"{decade}s"


# === Module-level global instance ===

_es_bm25: ElasticsearchBM25 | None = None


async def get_elasticsearch_bm25() -> ElasticsearchBM25:
    """Return the shared ElasticsearchBM25 instance, initializing if needed."""
    global _es_bm25
    if _es_bm25 is None:
        _es_bm25 = ElasticsearchBM25()
    await _es_bm25.initialize()
    return _es_bm25


async def close_elasticsearch_bm25() -> None:
    """Close the global Elasticsearch client."""
    global _es_bm25
    if _es_bm25:
        await _es_bm25.close()
        _es_bm25 = None
