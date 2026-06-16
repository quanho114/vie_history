"""Multi-layer caching strategy for RAG systems.

Layers:
1. L1: In-process LRU cache (hot data, microsecond access)
2. L2: Redis distributed cache (session data, seconds access)

Cache key strategy:
- query_hash: SHA-256 of normalized query + filters
- embedding_cache: normalized text → embedding
- session_cache: per-session conversation context
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import pickle
import time
from typing import Any, Callable, TypeVar

from app.core.logging import get_logger

logger = get_logger("cache")

T = TypeVar("T")


    # ─── L1 Cache: In-process LRU ───────────────────────────────────────────────


class L1Cache:
    """
    In-process LRU cache for ultra-low-latency hot data.

    Access time: ~10-100 microseconds
    Max size: 10,000 entries (~100MB for typical data)
    """

    def __init__(self, max_size: int = 10000):
        self._cache: dict[str, tuple[Any, float]] = {}
        self._access_order: list[str] = []
        self._max_size = max_size

    def get(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        value, expires_at = entry
        if expires_at < time.time():
            del self._cache[key]
            self._access_order.remove(key)
            return None
        # Move to end for LRU
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
        return value

    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        expires_at = time.time() + ttl_seconds
        if key not in self._cache and len(self._cache) >= self._max_size:
            oldest = self._access_order.pop(0)
            del self._cache[oldest]
        self._cache[key] = (value, expires_at)
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)

    def delete(self, key: str) -> None:
        self._cache.pop(key, None)
        if key in self._access_order:
            self._access_order.remove(key)

    def clear(self) -> None:
        self._cache.clear()
        self._access_order.clear()

    def __contains__(self, key: str) -> bool:
        return self.get(key) is not None


# ─── Cache Key Generation ────────────────────────────────────────────────────


class CacheKeyGenerator:
    """Generate consistent, granular cache keys using SHA-256."""

    @staticmethod
    def query_key(
        query: str,
        filters: dict | None = None,
        mode: str | None = None,
        session_id: str | None = None,
    ) -> str:
        normalized = " ".join(query.lower().split())
        payload = {
            "q": normalized,
            "f": sorted(filters.items()) if filters else None,
            "m": mode,
            "s": session_id,
        }
        key_hash = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=True).encode()
        ).hexdigest()[:16]
        return f"query:v1:{key_hash}"

    @staticmethod
    def embedding_key(texts: list[str]) -> str:
        normalized = "|".join(sorted([" ".join(t.lower().split()) for t in texts]))
        key_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"embed:v1:{key_hash}"

    @staticmethod
    def document_key(doc_id: str) -> str:
        return f"doc:v1:{doc_id}"

    @staticmethod
    def session_key(session_id: str) -> str:
        return f"session:v1:{session_id}"

    @staticmethod
    def intent_key(query: str) -> str:
        normalized = " ".join(query.lower().split())
        key_hash = hashlib.sha256(normalized.encode()).hexdigest()[:16]
        return f"intent:v1:{key_hash}"


# ─── L2 Cache: Redis ────────────────────────────────────────────────────────


class DistributedCache:
    """
    Redis-based distributed cache with L1 promotion.

    Features:
    - L1 in-process LRU for hot data
    - Request coalescing (thundering herd prevention)
    - Cache statistics
    """

    TTL_QUERY = 3600
    TTL_EMBEDDING = 86400
    TTL_DOCUMENT = 3600
    TTL_SESSION = 1800
    TTL_INTENT = 7200

    def __init__(self, l1_cache: L1Cache | None = None):
        self._l1 = l1_cache or L1Cache(10000)
        self._coalesce_lock = asyncio.Lock()
        self._pending: dict[str, asyncio.Future] = {}
        self._stats: dict[str, int] = {
            "hits": 0, "misses": 0,
            "l1_hits": 0, "l2_hits": 0, "errors": 0,
        }

    async def get(self, key: str) -> Any | None:
        val = self._l1.get(key)
        if val is not None:
            self._stats["l1_hits"] += 1
            self._stats["hits"] += 1
            return val

        try:
            from app.core.cache import cache
            raw = await cache.client.get(key)
            if raw is None:
                self._stats["misses"] += 1
                return None
            value = pickle.loads(raw)
            ttl = await cache.client.ttl(key)
            if ttl > 0:
                self._l1.set(key, value, ttl_seconds=min(ttl, 300))
            self._stats["l2_hits"] += 1
            self._stats["hits"] += 1
            return value
        except Exception as exc:
            self._stats["errors"] += 1
            logger.debug("cache_get_error", key=key[:30], error=str(exc))
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int,
        promotion_ttl: int = 300,
    ) -> None:
        self._l1.set(key, value, ttl_seconds=promotion_ttl)
        try:
            from app.core.cache import cache
            serialized = pickle.dumps(value)
            await cache.client.set(key, serialized, ex=ttl_seconds)
        except Exception as exc:
            self._stats["errors"] += 1
            logger.debug("cache_set_error", key=key[:30], error=str(exc))

    async def get_or_compute(
        self,
        key: str,
        compute_fn: Callable[[], Any],
        ttl_seconds: int,
    ) -> Any:
        """Get from cache or compute, with request coalescing."""
        cached = await self.get(key)
        if cached is not None:
            return cached

        async with self._coalesce_lock:
            if key in self._pending:
                future = self._pending[key]
            else:
                future = asyncio.Future()
                self._pending[key] = future

        # Outside the lock: either wait for existing, or compute new
        if key in self._pending and self._pending[key] is future:
            # We just created it — compute
            try:
                result = await compute_fn()
                future.set_result(result)
            except Exception as exc:
                future.set_exception(exc)
                raise
            finally:
                async with self._coalesce_lock:
                    self._pending.pop(key, None)
                await self.set(key, await self._resolve_future(future), ttl_seconds)
            return result
        else:
            # Another task is computing — wait
            return await self._resolve_future(future)

    async def _resolve_future(self, future: asyncio.Future) -> Any:
        try:
            return await future
        except Exception:
            raise

    async def invalidate(self, pattern: str) -> int:
        """Invalidate keys matching pattern."""
        try:
            from app.core.cache import cache
            keys = await cache.client.keys(pattern)
            if keys:
                await cache.client.delete(*keys)
                self._l1.clear()
                logger.info("cache_invalidated", pattern=pattern, count=len(keys))
                return len(keys)
        except Exception as exc:
            logger.error("cache_invalidate_error", error=str(exc))
        return 0

    def get_stats(self) -> dict[str, Any]:
        total = self._stats["hits"] + self._stats["misses"]
        return {
            **self._stats,
            "total_requests": total,
            "hit_rate": self._stats["hits"] / total if total > 0 else 0,
            "l1_size": len(self._l1._cache),
        }


# ─── Embedding Cache ────────────────────────────────────────────────────────


class EmbeddingCache:
    """Specialized cache for embedding results (deterministic, cache forever)."""

    def __init__(self, cache: DistributedCache):
        self._cache = cache

    async def get_embedding(
        self,
        texts: list[str],
        model_name: str,
    ) -> list | None:
        key = f"model:{model_name}:{CacheKeyGenerator.embedding_key(texts)}"
        return await self._cache.get(key)

    async def set_embedding(
        self,
        texts: list[str],
        model_name: str,
        embedding: list,
    ) -> None:
        key = f"model:{model_name}:{CacheKeyGenerator.embedding_key(texts)}"
        await self._cache.set(key, embedding, ttl_seconds=86400)


# ─── Query Result Cache ──────────────────────────────────────────────────────


class QueryResultCache:
    """Cache for agent query results."""

    def __init__(self, cache: DistributedCache):
        self._cache = cache

    async def get_result(
        self,
        query: str,
        filters: dict | None = None,
        mode: str | None = None,
    ) -> dict | None:
        key = CacheKeyGenerator.query_key(query, filters, mode)
        return await self._cache.get(key)

    async def set_result(
        self,
        query: str,
        result: dict,
        filters: dict | None = None,
        mode: str | None = None,
    ) -> None:
        key = CacheKeyGenerator.query_key(query, filters, mode)
        await self._cache.set(key, result, ttl_seconds=3600)

    async def invalidate_on_ingestion(self, doc_id: str) -> None:
        """Invalidate query cache when new documents are ingested."""
        await self._cache.invalidate("query:v1:*")


# ─── Global Instances ────────────────────────────────────────────────────────


_l1_cache: L1Cache | None = None
_distributed_cache: DistributedCache | None = None


def get_l1_cache() -> L1Cache:
    global _l1_cache
    if _l1_cache is None:
        _l1_cache = L1Cache(10000)
    return _l1_cache


def get_distributed_cache() -> DistributedCache:
    global _distributed_cache
    if _distributed_cache is None:
        _distributed_cache = DistributedCache(get_l1_cache())
    return _distributed_cache


def get_embedding_cache() -> EmbeddingCache:
    return EmbeddingCache(get_distributed_cache())


def get_query_result_cache() -> QueryResultCache:
    return QueryResultCache(get_distributed_cache())
