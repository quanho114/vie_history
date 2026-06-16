"""Redis Cache Client."""

import json
from typing import Any

import redis.asyncio as redis

from app.core.config import settings


class RedisCache:
    """Async Redis cache client."""

    def __init__(self):
        self._client: redis.Redis | None = None

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._client is None:
            self._client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._client:
            await self._client.close()
            self._client = None

    @property
    def client(self) -> redis.Redis:
        """Get Redis client."""
        if self._client is None:
            raise RuntimeError("Redis not connected. Call connect() first.")
        return self._client

    async def ping(self) -> bool:
        """Ping Redis server to check connection."""
        try:
            return await self.client.ping()
        except Exception:
            return False

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        try:
            value = await self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
    ) -> bool:
        """Set value in cache with TTL."""
        try:
            serialized = json.dumps(value, ensure_ascii=False, default=str)
            await self.client.set(key, serialized, ex=ttl)
            return True
        except Exception:
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        try:
            await self.client.delete(key)
            return True
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        try:
            return await self.client.exists(key) > 0
        except Exception:
            return False

    async def incr(self, key: str, amount: int = 1) -> int:
        """Increment counter."""
        try:
            return await self.client.incrby(key, amount)
        except Exception:
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on key."""
        try:
            return await self.client.expire(key, ttl)
        except Exception:
            return False

    async def keys(self, pattern: str) -> list[str]:
        """Get keys matching pattern."""
        try:
            return await self.client.keys(pattern)
        except Exception:
            return []

    # === CACHE HELPERS ===

    async def cache_query_result(
        self,
        query_hash: str,
        result: dict,
        ttl: int = 1800,
    ) -> bool:
        """Cache query result."""
        key = f"query:{query_hash}"
        return await self.set(key, result, ttl)

    async def get_cached_query(self, query_hash: str) -> dict | None:
        """Get cached query result."""
        key = f"query:{query_hash}"
        return await self.get(key)

    async def cache_llm_response(
        self,
        prompt_hash: str,
        response: str,
        ttl: int = 86400,
    ) -> bool:
        """Cache LLM response."""
        key = f"llm:{prompt_hash}"
        return await self.set(key, {"response": response}, ttl)

    async def get_cached_llm(self, prompt_hash: str) -> str | None:
        """Get cached LLM response."""
        key = f"llm:{prompt_hash}"
        data = await self.get(key)
        return data.get("response") if data else None


# === GLOBAL INSTANCE ===
cache = RedisCache()


async def get_cache() -> RedisCache:
    """Dependency for getting cache."""
    return cache
