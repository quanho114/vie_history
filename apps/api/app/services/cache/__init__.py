"""Cache service layer."""

from app.services.cache.query_cache import QueryCache, get_query_cache

__all__ = ["QueryCache", "get_query_cache"]
