"""API routes."""

from app.api.routes.auth import router as auth_router
from app.api.routes.query import router as query_router
from app.api.routes.sessions import router as sessions_router
from app.api.routes.ingest import router as ingest_router
from app.api.routes.documents import router as documents_router
from app.api.routes.admin import router as admin_router
from app.api.routes.feedback import router as feedback_router
from app.api.routes.wiki import router as wiki_router
from app.api.routes.brain import router as brain_router
from app.api.routes.timeline import router as timeline_router
from app.api.routes.graph import router as graph_router
from app.api.routes.projects import router as projects_router
from app.api.routes.drafts import router as drafts_router
from app.api.routes.safety import router as safety_router

__all__ = [
    "auth_router",
    "query_router",
    "sessions_router",
    "ingest_router",
    "documents_router",
    "admin_router",
    "feedback_router",
    "wiki_router",
    "brain_router",
    "timeline_router",
    "graph_router",
    "projects_router",
    "drafts_router",
    "safety_router",
]
