"""API v1 — initial stable release of HistoriAI API.

All routes under /api/v1/* are considered stable.
Breaking changes will require a new version (v2).

Endpoint conventions:
    - /auth/*     → Authentication & user management
    - /documents/* → Document management
    - /query/*    → RAG query pipeline
    - /ingest/*   → Document ingestion
    - /projects/* → Project/workspace management
    - /sessions/* → Chat session management
    - /admin/*    → Admin-only endpoints
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    auth,
    admin,
    documents,
    query,
    ingest,
    sessions,
    projects,
    drafts,
    feedback,
    graph,
    brain,
    timeline,
    wiki,
    safety,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(query.router, prefix="/query", tags=["Query"])
api_router.include_router(ingest.router, prefix="/ingest", tags=["Ingestion"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(projects.router, prefix="/projects", tags=["Projects"])
api_router.include_router(drafts.router, prefix="/drafts", tags=["Drafts"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["Feedback"])
api_router.include_router(graph.router, prefix="/graph", tags=["Knowledge Graph"])
api_router.include_router(brain.router, prefix="/brain", tags=["Second Brain"])
api_router.include_router(timeline.router, prefix="/timeline", tags=["Timeline"])
api_router.include_router(wiki.router, prefix="/wiki", tags=["Wiki"])
api_router.include_router(safety.router, prefix="/safety", tags=["Safety"])

__all__ = ["api_router"]
