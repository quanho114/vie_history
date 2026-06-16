"""Unit tests for the Redis Rate Limiter."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_rate_limiter_allowed():
    """Test that RateLimiter allows requests under limit."""
    limiter = RateLimiter(limit=5, window=60)
    
    # Use MagicMock for the synchronous redis client
    mock_redis = MagicMock()
    # Use AsyncMock for the pipeline since its execute method is async
    mock_pipeline = AsyncMock()
    
    # Mock pipeline async methods
    mock_pipeline.zremrangebyscore = AsyncMock()
    mock_pipeline.zcard = AsyncMock()
    mock_pipeline.zadd = AsyncMock()
    mock_pipeline.expire = AsyncMock()
    
    # Mock pipe.execute() to return:
    # 1. zremrangebyscore output (e.g. 0)
    # 2. zcard output (e.g. 3 requests, which is <= 5)
    # 3. zadd output
    # 4. expire output
    mock_pipeline.execute = AsyncMock(return_value=(0, 3, 1, True))
    mock_redis.pipeline.return_value = mock_pipeline

    with patch("app.core.rate_limiter.cache") as mock_cache_module:
        # Mock cache client attribute
        mock_cache_module.client = mock_redis
        
        allowed = await limiter.is_allowed("127.0.0.1")
        assert allowed is True
        
        # Verify pipeline calls
        mock_redis.pipeline.assert_called_once()
        mock_pipeline.zremrangebyscore.assert_called_once()
        mock_pipeline.zcard.assert_called_once()
        mock_pipeline.zadd.assert_called_once()
        mock_pipeline.expire.assert_called_once()


@pytest.mark.asyncio
async def test_rate_limiter_blocked():
    """Test that RateLimiter blocks requests exceeding the limit."""
    limiter = RateLimiter(limit=5, window=60)
    
    mock_redis = MagicMock()
    mock_pipeline = AsyncMock()
    
    mock_pipeline.zremrangebyscore = AsyncMock()
    mock_pipeline.zcard = AsyncMock()
    mock_pipeline.zadd = AsyncMock()
    mock_pipeline.expire = AsyncMock()
    
    # Mock pipe.execute() to return 6 requests (> 5 limit)
    mock_pipeline.execute = AsyncMock(return_value=(0, 6, 1, True))
    mock_redis.pipeline.return_value = mock_pipeline

    with patch("app.core.rate_limiter.cache") as mock_cache_module:
        mock_cache_module.client = mock_redis
        
        allowed = await limiter.is_allowed("127.0.0.1")
        assert allowed is False
