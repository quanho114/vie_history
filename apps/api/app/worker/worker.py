"""Arq worker task definitions for background jobs.

Arq is chosen over RQ because it natively supports async/await,
integrates cleanly with FastAPI's async ecosystem, and uses
Pydantic for job result serialization.

Run worker with:
    arq app.worker.settings.WorkerSettings

Or from project root:
    PYTHONPATH=. arq apps/api/app/worker/settings.py
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import structlog

from app.core.config import settings
from app.core.database import async_session
from app.models.document import Document, DocumentChunk
from app.models.evolution import KnowledgeDraft

logger = structlog.get_logger("arq_tasks")


# ─── Redis Settings ──────────────────────────────────────────────────────────


def redis_settings() -> "RedisSettings":
    """Redis connection for Arq worker."""
    from arq.connections import RedisSettings as ArqRedisSettings

    return ArqRedisSettings.from_dsn(settings.REDIS_URL)


# ─── Task Functions ──────────────────────────────────────────────────────────


async def process_ingestion(ctx: dict, url: str, user_id: str | None = None, tags: list[str] | None = None) -> dict[str, Any]:
    """
    Background ingestion task — fetches, cleans, chunks, and indexes a document.

    Runs asynchronously, doesn't block the API request.
    """
    from app.services.ingestion.service import IngestService

    job_id = ctx.get("job_id", "unknown")
    logger.info("ingest_task_started", job_id=job_id, url=url[:100] if url else "")

    try:
        service = IngestService()
        result = await service.ingest_url(url=url, user_id=user_id)

        return {
            "success": True,
            "doc_id": result.get("doc_id"),
            "chunk_count": result.get("chunk_count", 0),
            "title": result.get("title", ""),
            "completed_at": datetime.utcnow().isoformat(),
        }
    except Exception as exc:
        logger.error("ingest_task_failed", job_id=job_id, error=str(exc))
        return {
            "success": False,
            "error": str(exc),
            "completed_at": datetime.utcnow().isoformat(),
        }


async def process_bulk_ingestion(ctx: dict, urls: list[dict]) -> dict[str, Any]:
    """Bulk ingest multiple URLs with controlled concurrency."""
    import asyncio

    logger.info("bulk_ingest_started", url_count=len(urls))

    results: dict[str, Any] = {"success": 0, "failed": 0, "errors": []}

    semaphore = asyncio.Semaphore(3)

    async def ingest_one(url_params: dict) -> dict:
        async with semaphore:
            job = await ctx["redis"].enqueue_job(
                "process_ingestion",
                url_params.get("url", ""),
                url_params.get("user_id"),
                url_params.get("tags"),
                _max_retries=3,
            )
            return {"url": url_params.get("url"), "job_id": job.job_id}

    tasks = [ingest_one(p) for p in urls]
    enqueued = await asyncio.gather(*tasks, return_exceptions=True)

    results["enqueued_count"] = len([e for e in enqueued if not isinstance(e, Exception)])
    results["failed_count"] = len([e for e in enqueued if isinstance(e, Exception)])

    return results


async def index_document_task(ctx: dict, doc_id: str) -> dict[str, Any]:
    """Background task to index a document in Qdrant and Meilisearch."""
    results: dict[str, bool] = {"qdrant": False, "meilisearch": False}

    try:
        from app.services.retrieval.vector_search import VectorSearch

        vs = VectorSearch()
        await vs.index_document(doc_id)
        results["qdrant"] = True
    except Exception as exc:
        logger.warning("qdrant_index_failed", doc_id=doc_id, error=str(exc))

    try:
        from app.services.retrieval.meilisearch_bm25 import get_meilisearch_bm25

        meili = await get_meilisearch_bm25()
        await meili.remove_by_document_id(doc_id)
        results["meilisearch"] = True
    except Exception as exc:
        logger.warning("meilisearch_index_failed", doc_id=doc_id, error=str(exc))

    return results


async def cleanup_stale_drafts(ctx: dict) -> dict[str, Any]:
    """Remove stale knowledge drafts pending review > 30 days."""
    from sqlalchemy import delete, and_

    async with async_session() as db:
        cutoff = datetime.utcnow() - timedelta(days=30)
        stmt = delete(KnowledgeDraft).where(
            and_(
                KnowledgeDraft.status == "pending",
                KnowledgeDraft.created_at < cutoff,
            )
        )
        result = await db.execute(stmt)
        await db.commit()

        logger.info("cleanup_stale_drafts", deleted_count=result.rowcount)
        return {"deleted_count": result.rowcount}


# ─── Re-export RedisSettings for settings module ─────────────────────────────
from arq.connections import RedisSettings

__all__ = [
    "process_ingestion",
    "process_bulk_ingestion",
    "index_document_task",
    "cleanup_stale_drafts",
    "redis_settings",
    "RedisSettings",
]
