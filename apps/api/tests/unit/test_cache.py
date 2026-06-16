# apps/api/tests/unit/test_cache.py
import pytest
from unittest.mock import AsyncMock, patch
from app.core.cache import RedisCache


class TestRedisCache:
    @pytest.fixture
    def cache(self):
        return RedisCache()

    @pytest.mark.asyncio
    async def test_get_returns_none_when_disconnected(self, cache):
        result = await cache.get("any_key")
        assert result is None

    @pytest.mark.asyncio
    async def test_set_returns_false_when_disconnected(self, cache):
        result = await cache.set("key", "value")
        assert result is False
