"""Redis distributed lock using SET NX EX pattern."""
from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, AsyncGenerator

if TYPE_CHECKING:
    import redis.asyncio as redis


class RedisLock:
    """Async Redis distributed lock with auto-renewal support.

    Uses the SET NX EX pattern for atomic lock acquisition with TTL.
    Only the owner (matching token) can release the lock.

    Features:
    - Atomic acquisition with NX (only if not exists)
    - Automatic expiry via EX to prevent deadlocks
    - Lua script for atomic check-and-release
    - Async context manager interface
    """

    _RELEASE_SCRIPT = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """

    def __init__(
        self,
        redis_client: "redis.Redis",
        key: str,
        ttl: int = 30,
        retry_interval: float = 0.1,
        max_retries: int = 100,
    ):
        self.redis = redis_client
        self.key = f"lock:{key}"
        self.ttl = ttl
        self.retry_interval = retry_interval
        self.max_retries = max_retries
        self.token = str(uuid.uuid4())
        self._locked = False
        self._script_sha: str | None = None

    async def _ensure_script(self) -> str:
        """Load Lua script if not already loaded."""
        if self._script_sha is None:
            self._script_sha = await self.redis.script_load(self._RELEASE_SCRIPT)
        return self._script_sha

    async def acquire(self) -> bool:
        """Acquire the lock. Returns True if acquired, False otherwise."""
        for _ in range(self.max_retries):
            acquired = await self.redis.set(
                self.key,
                self.token,
                nx=True,
                ex=self.ttl,
            )
            if acquired:
                self._locked = True
                return True
            await asyncio.sleep(self.retry_interval)
        return False

    async def release(self) -> bool:
        """Release the lock if we own it (Lua script for atomicity)."""
        if not self._locked:
            return False

        script_sha = await self._ensure_script()
        try:
            result = await self.redis.evalsha(script_sha, 1, self.key, self.token)
        except Exception:
            # Script was flushed — reload and retry once
            self._script_sha = None
            script_sha = await self._ensure_script()
            result = await self.redis.evalsha(script_sha, 1, self.key, self.token)

        self._locked = False
        return bool(result)

    async def extend(self, additional_ttl: int | None = None) -> bool:
        """Extend the lock TTL if we still own it."""
        if not self._locked:
            return False

        ttl = additional_ttl or self.ttl
        lua = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """
        result = await self.redis.eval(lua, 1, self.key, self.token, ttl)
        return bool(result)

    async def __aenter__(self) -> "RedisLock":
        acquired = await self.acquire()
        if not acquired:
            raise RuntimeError(f"Could not acquire lock: {self.key}")
        return self

    async def __aexit__(self, *args) -> None:
        await self.release()


@asynccontextmanager
async def distributed_lock(
    redis_client: "redis.Redis",
    key: str,
    ttl: int = 30,
    retry_interval: float = 0.1,
    max_retries: int = 100,
) -> AsyncGenerator[RedisLock, None]:
    """Context manager for distributed locking."""
    lock = RedisLock(
        redis_client,
        key,
        ttl=ttl,
        retry_interval=retry_interval,
        max_retries=max_retries,
    )
    acquired = await lock.acquire()
    if not acquired:
        raise RuntimeError(f"Could not acquire lock: {key}")
    try:
        yield lock
    finally:
        await lock.release()


# ─── Task Lock (Idempotency) ───────────────────────────────────────────────────


class TaskLock:
    """Distributed lock for preventing duplicate task execution.

    Uses Redis to track in-flight tasks with idempotency keys.
    A task with the same key will be rejected if already running.

    Usage:
        lock = TaskLock(redis, "ingest:url:abc123")
        if await lock.try_acquire():
            try:
                await do_work()
            finally:
                await lock.release()
    """

    _CLEAR_SCRIPT = """
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """

    def __init__(
        self,
        redis_client: "redis.Redis",
        task_key: str,
        ttl: int = 3600,
    ):
        self.redis = redis_client
        self.key = f"task:{task_key}"
        self.ttl = ttl
        self.token = str(uuid.uuid4())
        self._acquired = False
        self._script_sha: str | None = None

    async def _ensure_script(self) -> str:
        if self._script_sha is None:
            self._script_sha = await self.redis.script_load(self._CLEAR_SCRIPT)
        return self._script_sha

    async def try_acquire(self) -> bool:
        """Try to acquire the task lock. Returns True if acquired, False if already running."""
        acquired = await self.redis.set(
            self.key,
            self.token,
            nx=True,
            ex=self.ttl,
        )
        self._acquired = bool(acquired)
        return self._acquired

    async def release(self) -> bool:
        """Release the task lock if we own it."""
        if not self._acquired:
            return False

        script_sha = await self._ensure_script()
        try:
            result = await self.redis.evalsha(script_sha, 1, self.key, self.token)
        except Exception:
            self._script_sha = None
            script_sha = await self._ensure_script()
            result = await self.redis.evalsha(script_sha, 1, self.key, self.token)

        self._acquired = False
        return bool(result)

    @property
    def is_running(self) -> bool:
        """Check if task is currently running (lock held)."""
        return self._acquired


@asynccontextmanager
async def task_lock(
    redis_client: "redis.Redis",
    task_key: str,
    ttl: int = 3600,
) -> AsyncGenerator[TaskLock, None]:
    """Context manager for idempotent task locking.

    Raises RuntimeError if the task is already running.
    """
    lock = TaskLock(redis_client, task_key, ttl=ttl)
    acquired = await lock.try_acquire()
    if not acquired:
        raise RuntimeError(f"Task already running: {task_key}")
    try:
        yield lock
    finally:
        await lock.release()
