"""Fine-grained RBAC with permission-based access control."""

from __future__ import annotations

from enum import Enum
from functools import wraps
from typing import Callable, Any

from fastapi import HTTPException, status

from app.core.logging import get_logger

logger = get_logger("rbac")


class Permission(str, Enum):
    """Granular permissions for HistoriAI."""
    # Document
    DOCUMENT_READ = "document:read"
    DOCUMENT_CREATE = "document:create"
    DOCUMENT_UPDATE = "document:update"
    DOCUMENT_DELETE = "document:delete"
    DOCUMENT_APPROVE = "document:approve"
    # Query
    QUERY_EXECUTE = "query:execute"
    QUERY_STREAM = "query:stream"
    # Ingestion
    INGEST_URL = "ingest:url"
    INGEST_BULK = "ingest:bulk"
    # Admin
    ADMIN_USERS = "admin:users"
    ADMIN_DRAFTS = "admin:drafts"
    ADMIN_STATS = "admin:stats"
    ADMIN_SETTINGS = "admin:settings"
    # MCP
    MCP_TOOL_LIST = "mcp:tool:list"
    MCP_TOOL_READ = "mcp:tool:read"
    MCP_TOOL_WRITE = "mcp:tool:write"
    # Knowledge Graph
    GRAPH_READ = "graph:read"
    GRAPH_WRITE = "graph:write"
    GRAPH_ADMIN = "graph:admin"


ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "anonymous": {
        Permission.DOCUMENT_READ,
        Permission.QUERY_EXECUTE,
        Permission.GRAPH_READ,
    },
    "user": {
        Permission.DOCUMENT_READ,
        Permission.QUERY_EXECUTE,
        Permission.QUERY_STREAM,
        Permission.INGEST_URL,
        Permission.GRAPH_READ,
    },
    "contributor": {
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_CREATE,
        Permission.QUERY_EXECUTE,
        Permission.QUERY_STREAM,
        Permission.INGEST_URL,
        Permission.INGEST_BULK,
        Permission.GRAPH_READ,
        Permission.GRAPH_WRITE,
    },
    "moderator": {
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_CREATE,
        Permission.DOCUMENT_UPDATE,
        Permission.DOCUMENT_APPROVE,
        Permission.INGEST_URL,
        Permission.INGEST_BULK,
        Permission.ADMIN_DRAFTS,
        Permission.GRAPH_READ,
        Permission.GRAPH_WRITE,
    },
    "admin": set(Permission),
}


def get_user_permissions(role: str) -> set[Permission]:
    """Get all permissions for a role."""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(role: str, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in ROLE_PERMISSIONS.get(role, set())


def require_permission(*permissions: Permission, require_all: bool = False):
    """
    Decorator to enforce permission checks on route handlers.

    Usage:
        @router.post("/documents")
        @require_permission(Permission.DOCUMENT_CREATE)
        async def create_document(...):
            ...

        @router.delete("/documents/{doc_id}")
        @require_permission(Permission.DOCUMENT_DELETE, Permission.DOCUMENT_READ, require_all=True)
        async def delete_document(...):
            ...
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = kwargs.get("current_user")

            if user is None:
                raise HTTPException(status_code=401, detail="Authentication required")

            user_permissions = get_user_permissions(getattr(user, "role", "anonymous"))

            if require_all:
                missing = [p for p in permissions if p not in user_permissions]
                if missing:
                    logger.warning(
                        "permission_denied",
                        user_id=getattr(user, "id", None),
                        role=getattr(user, "role", None),
                        missing=[p.value for p in missing],
                    )
                    raise HTTPException(
                        status_code=403,
                        detail=f"Missing permissions: {[p.value for p in missing]}",
                    )
            else:
                if not any(p in user_permissions for p in permissions):
                    logger.warning(
                        "permission_denied_any",
                        user_id=getattr(user, "id", None),
                        role=getattr(user, "role", None),
                        required_any=[p.value for p in permissions],
                    )
                    raise HTTPException(
                        status_code=403,
                        detail="Insufficient permissions",
                    )

            return await func(*args, **kwargs)

        return wrapper
    return decorator
