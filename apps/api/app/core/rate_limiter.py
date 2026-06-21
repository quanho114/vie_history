"""Sliding Window Redis-based Rate Limiter."""

import time
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.cache import cache
from app.core.logging import logger
from app.core.config import settings
from app.core.audit import get_audit_logger


class RateLimiter:
    """Sliding window rate limiter using Redis sorted sets."""

    def __init__(self, limit: int = 60, window: int = 60):
        self.limit = limit
        self.window = window

    async def is_allowed(self, key: str) -> bool:
        """
        Check if request under the given key is allowed.
        Uses a sliding window in Redis.
        """
        try:
            # Fallback if Redis not connected
            redis_client = cache.client
        except Exception:
            # If Redis is down, we fail-open in dev/test, fail-closed in prod
            if settings.is_production:
                logger.error("rate_limiter_redis_offline_fail_closed")
                return False
            logger.warning("rate_limiter_redis_offline_fail_open")
            return True

        try:
            now = time.time()
            redis_key = f"rate_limit:{key}"
            
            # Use Redis pipeline for atomicity
            pipe = redis_client.pipeline()
            # 1. Remove elements older than window
            pipe.zremrangebyscore(redis_key, 0, now - self.window)
            # 2. Get card of remaining elements
            pipe.zcard(redis_key)
            # 3. Add current timestamp
            pipe.zadd(redis_key, {str(now): now})
            # 4. Set TTL on key
            pipe.expire(redis_key, self.window)
            
            # Execute pipeline
            _, current_count, _, _ = await pipe.execute()
            
            if current_count > self.limit:
                logger.warning("rate_limit_exceeded", key=key, count=current_count, limit=self.limit)
                return False
                
            return True
        except Exception as exc:
            logger.error("rate_limiter_error", error=str(exc))
            return True  # Fail-open on unexpected errors


class RateLimitMiddleware:
    """
    Pure ASGI Middleware to enforce rate limits per user + per IP.

    Authenticated requests: rate limit by user_id (from JWT).
    Unauthenticated requests: rate limit by client IP.
    """

    def __init__(self, app, limit: int = 60, window: int = 60):
        self.app = app
        self.limiter = RateLimiter(limit=limit, window=window)

    def _get_user_id_from_headers(self, headers: dict[bytes, bytes]) -> str | None:
        """Extract user_id from JWT Bearer token if present."""
        auth_header = headers.get(b"authorization", b"").decode("latin-1")
        if not auth_header.startswith("Bearer "):
            return None
        token = auth_header[7:]
        try:
            import jwt
            from app.core.config import settings
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=["HS256"],
                options={"verify_signature": False},
            )
            return payload.get("sub") or payload.get("user_id")
        except Exception:
            return None

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in ["/health", "/api/v1/health", "/docs", "/redoc", "/metrics"]:
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        
        # Check bypass
        if settings.APP_ENV in ("development", "testing") and headers.get(b"x-bypass-rate-limit") == b"true":
            await self.app(scope, receive, send)
            return

        # Determine rate limit key: user_id if authenticated, else IP
        user_id = self._get_user_id_from_headers(headers)
        if user_id:
            key = f"user:{user_id}"
        else:
            client = scope.get("client")
            key = f"ip:{client[0] if client else 'unknown'}"

        allowed = await self.limiter.is_allowed(key)
        if not allowed:
            client_ip = scope.get("client", ["unknown"])[0] if scope.get("client") else "unknown"
            get_audit_logger().log_rate_limit_exceeded(
                ip_address=client_ip,
                path=path,
                user_id=user_id,
            )
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"retry-after", str(self.limiter.window).encode("latin-1")),
                ],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"detail": "Too many requests. Please try again later."}',
                "more_body": False,
            })
            return

        await self.app(scope, receive, send)

