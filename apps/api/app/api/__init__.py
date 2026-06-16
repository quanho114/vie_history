"""API Routes."""

from app.api.routes.auth import router as auth_router
from app.api.routes.query import router as query_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.ingest import router as ingest_router
from app.api.routes.documents import router as documents_router
from app.api.routes.admin import router as admin_router
from app.api.routes.feedback import router as feedback_router

__all__ = [
    "auth_router",
    "query_router",
    "sessions_router",
    "ingest_router",
    "documents_router",
    "admin_router",
    "feedback_router",
]
