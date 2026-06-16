"""Query-level caching service with Redis."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("query_cache")


def _normalize_query(query: str) -> str:
    """Normalize query for consistent cache keys."""
    return query.lower().strip()


def _query_cache_key(query: str, filters: dict | None = None) -> str:
    """Generate a deterministic cache key for a query + filters pair."""
    from app.core.context import (
        active_provider_var,
        gemini_model_var,
        gemini_key_var,
        groq_model_var,
        groq_key_var,
        openai_model_var,
        openai_key_var,
        ollama_model_var,
    )

    normalized = _normalize_query(query)
    filters_str = json.dumps(filters or {}, sort_keys=True, ensure_ascii=False)
    provider = active_provider_var.get() or settings.LLM_PROVIDER
    model = {
        "gemini": gemini_model_var.get() or "gemini-1.5-pro",
        "groq": groq_model_var.get() or "llama-3.3-70b-versatile",
        "openai": openai_model_var.get() or settings.OPENAI_MODEL,
        "openrouter": openai_model_var.get() or settings.OPENAI_MODEL,
        "ollama": ollama_model_var.get() or settings.OLLAMA_MODEL,
    }.get(provider, "")
    api_key = {
        "gemini": gemini_key_var.get(),
        "groq": groq_key_var.get(),
        "openai": openai_key_var.get(),
        "openrouter": openai_key_var.get(),
    }.get(provider) or ""
    key_fingerprint = hashlib.sha256(api_key.encode()).hexdigest()[:8] if api_key else "no-key"
    combined = f"{normalized}|{filters_str}|provider={provider}|model={model}|key={key_fingerprint}"
    digest = hashlib.sha256(combined.encode()).hexdigest()[:16]
    return f"query_cache:{digest}"


class QueryCache:
    """
    Query result caching layer.

    Caches the complete AgentResult so that subsequent identical
    queries (same text + same filters) return instantly from Redis.
    """

    def __init__(self, cache) -> None:
        self._cache = cache
        # TTL in seconds
        self._result_ttl = 1800  # 30 minutes
        self._llm_ttl = 86400   # 24 hours for LLM responses

    async def get(self, query: str, filters: dict | None = None) -> dict[str, Any] | None:
        """
        Retrieve cached query result.

        Returns None on miss or cache error — callers must proceed normally.
        """
        if self._cache is None:
            return None
        if len(_normalize_query(query)) < 8:
            return None

        key = _query_cache_key(query, filters)
        try:
            result = await self._cache.get(key)
            if result:
                logger.debug("query_cache_hit", key=key)
            return result
        except Exception as exc:
            logger.warning("query_cache_get_failed", key=key, error=str(exc))
            return None

    async def set(
        self,
        query: str,
        filters: dict | None,
        result: dict[str, Any],
    ) -> None:
        """
        Store query result in cache.

        Silently fails on errors — cache misses should not break the pipeline.
        """
        if self._cache is None:
            return
        if len(_normalize_query(query)) < 8:
            return

        key = _query_cache_key(query, filters)
        try:
            await self._cache.set(key, result, ttl=self._result_ttl)
            logger.debug("query_cache_set", key=key)
        except Exception as exc:
            logger.warning("query_cache_set_failed", key=key, error=str(exc))

    async def clear_all(self) -> list[str]:
        """
        Clear all cached query results.

        Call after bulk ingestion or schema changes.
        Returns deleted keys (may be empty on error).
        """
        if self._cache is None or self._cache._client is None:
            return []

        try:
            keys = [k async for k in self._cache._client.scan_iter("query_cache:*")]
            if keys:
                await self._cache._client.delete(*keys)
            return keys
        except Exception as exc:
            logger.warning("query_cache_clear_failed", error=str(exc))
            return []


# Lazy-initialized singleton
_query_cache: QueryCache | None = None


def get_query_cache() -> QueryCache:
    """Get or create the query cache singleton."""
    global _query_cache
    if _query_cache is None:
        from app.core.cache import cache
        _query_cache = QueryCache(cache)
    return _query_cache
