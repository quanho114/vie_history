"""Redis-based distributed locking for race condition prevention."""

from contextlib import asynccontextmanager
from datetime import timedelta
from typing import AsyncGenerator
import asyncio
import uuid

import redis.asyncio as redis

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("distributed_lock")

# ─── Lock Implementation ──────────────────────────────────────────────────────


class DistributedLock:
    """
    Redis-based distributed lock using SET NX with expiry.

    Implementation of Redlock algorithm (simplified single-node version).
    For production with multiple Redis instances, use redlock-py.

    Features:
    - Automatic expiry to prevent deadlocks
    - Token-based ownership verification (only owner can release)
    - Async context manager interface
    """

    _RELEASE_SCRIPT = """
    if redis.call('get', KEYS[1]) == ARGV[1] then
        return redis.call('del', KEYS[1])
    else
        return 0
    end
    """

    def __init__(
        self,
        redis_url: str | None = None,
        lock_prefix: str = "dlock",
    ):
        self._redis_url = redis_url or settings.REDIS_URL
        self._redis: redis.Redis | None = None
        self._lock_prefix = lock_prefix
        self._script_sha: str | None = None

    async def _get_redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.from_url(self._redis_url, decode_responses=False)
            self._script_sha = await self._redis.script_load(self._RELEASE_SCRIPT)
        return self._redis

    async def acquire(
        self,
        resource: str,
        timeout: timedelta = timedelta(seconds=30),
        retry_interval: float = 0.1,
        max_retries: int = 50,
    ) -> str | None:
        """
        Acquire a lock on a resource.

        Args:
            resource: Unique resource identifier
            timeout: Lock expiry time (prevents deadlocks)
            retry_interval: Time between acquisition attempts
            max_retries: Max attempts before giving up

        Returns:
            Lock token if acquired, None if failed
        """
        client = await self._get_redis()
        key = f"{self._lock_prefix}:{resource}"
        token = str(uuid.uuid4())

        for attempt in range(max_retries):
            acquired = await client.set(
                key,
                token,
                nx=True,
                ex=int(timeout.total_seconds()),
            )

            if acquired:
                logger.debug("lock_acquired", resource=resource, token=token[:8])
                return token

            await asyncio.sleep(retry_interval)

        logger.warning("lock_acquisition_failed", resource=resource, attempts=max_retries)
        return None

    async def release(self, resource: str, token: str) -> bool:
        """
        Release a lock. Only the owner (matching token) can release.

        Uses Lua script for atomic check-and-delete.
        """
        client = await self._get_redis()
        key = f"{self._lock_prefix}:{resource}"

        try:
            result = await client.evalsha(
                self._script_sha,
                1,
                key,
                token,
            )
            released = bool(result)
            if released:
                logger.debug("lock_released", resource=resource)
            return released
        except redis.exceptions.NoScriptError:
            self._script_sha = await client.script_load(self._RELEASE_SCRIPT)
            return await self.release(resource, token)

    async def extend(
        self,
        resource: str,
        token: str,
        timeout: timedelta,
    ) -> bool:
        """Extend a lock's TTL if we still own it."""
        client = await self._get_redis()
        key = f"{self._lock_prefix}:{resource}"

        current = await client.get(key)
        if current and current.decode() == token:
            await client.expire(key, int(timeout.total_seconds()))
            return True
        return False

    @asynccontextmanager
    async def lock(
        self,
        resource: str,
        timeout: timedelta = timedelta(seconds=30),
    ) -> AsyncGenerator[bool, None]:
        """
        Async context manager for distributed locking.

        Usage:
            async with distributed_lock.lock("document:123:index"):
                await index_document("123")
        """
        token = await self.acquire(resource, timeout)
        if token is None:
            raise TimeoutError(f"Could not acquire lock for {resource}")

        try:
            yield True
        finally:
            await self.release(resource, token)

    async def close(self) -> None:
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()


# ─── Singleton Instance ────────────────────────────────────────────────────────

_distributed_lock: DistributedLock | None = None


def get_distributed_lock() -> DistributedLock:
    """Get the global distributed lock instance."""
    global _distributed_lock
    if _distributed_lock is None:
        _distributed_lock = DistributedLock()
    return _distributed_lock


# ─── Convenience Context Manager ───────────────────────────────────────────────


distributed_lock = get_distributed_lock()
