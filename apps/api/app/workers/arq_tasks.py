"""Arq worker tasks for async background processing."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from arq import cron
from arq.connections import RedisSettings
from pydantic import BaseModel


class TaskContext(BaseModel):
    """Arq task context schema."""

    redis_url: str


async def process_ingest_batch(
    ctx: dict[str, Any],
    job_id: str,
    urls: list[str],
    user_id: str,
) -> dict[str, Any]:
    """Process a batch of URLs for ingestion.

    Args:
        ctx: Arq task context (contains redis_url)
        job_id: Unique job identifier
        urls: List of URLs to ingest
        user_id: User who initiated the ingestion

    Returns:
        Summary dict with processed count and per-URL results
    """
    from app.core.database import async_session
    from app.services.ingestion.service import IngestService

    service = IngestService()
    results = []

    async with async_session() as db:
        for url in urls:
            try:
                job = await service.ingest_url(db=db, url=url, user_id=user_id)
                results.append({
                    "url": url,
                    "status": "success" if job.status == "done" else "failed",
                    "job_id": job.id,
                    "stage": job.stage,
                    "error": job.error_message if job.status == "failed" else None,
                })
            except Exception as e:
                results.append({
                    "url": url,
                    "status": "error",
                    "error": str(e),
                })

    processed = len(urls)
    succeeded = sum(1 for r in results if r["status"] == "success")
    failed = processed - succeeded

    return {
        "job_id": job_id,
        "processed": processed,
        "succeeded": succeeded,
        "failed": failed,
        "results": results,
    }


async def cleanup_expired_sessions(ctx: dict[str, Any]) -> dict[str, Any]:
    """Periodic cleanup of expired sessions.

    Runs daily at 3 AM to remove sessions not updated in 30 days.

    Args:
        ctx: Arq task context

    Returns:
        Summary dict with number of deleted sessions
    """
    from app.core.database import async_session
    from app.models.session import Session
    from sqlalchemy import delete

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    async with async_session() as db:
        result = await db.execute(
            delete(Session).where(Session.updated_at < cutoff)
        )
        await db.commit()
        deleted = result.rowcount

    return {
        "task": "cleanup_expired_sessions",
        "deleted": deleted,
        "cutoff_days": 30,
        "cutoff_at": cutoff.isoformat(),
    }


async def refresh_embeddings(ctx: dict[str, Any]) -> dict[str, Any]:
    """Periodic re-embedding of documents for stale/missing embeddings.

    Runs daily at 4 AM to find chunks without embeddings and regenerate them.

    Args:
        ctx: Arq task context

    Returns:
        Summary dict with pending count and processed count
    """
    from app.core.database import async_session
    from app.models.document import DocumentChunk
    from app.services.retrieval.embedder import Embedder
    from app.services.retrieval.vector_search import VectorSearch
    from sqlalchemy import select

    embedder = Embedder()
    vector_search = VectorSearch()
    batch_size = 32
    processed = 0

    async with async_session() as db:
        while True:
            result = await db.execute(
                select(DocumentChunk).where(
                    DocumentChunk.chunk_metadata["embedding_stale"].astext == "true"
                ).limit(batch_size)
            )
            chunks = list(result.scalars().all())

            if not chunks:
                # Fallback: find chunks with no vector_id
                result = await db.execute(
                    select(DocumentChunk).where(
                        DocumentChunk.vector_id.is_(None)
                    ).limit(batch_size)
                )
                chunks = list(result.scalars().all())

            if not chunks:
                break

            # Re-embed and update
            texts = [chunk.content for chunk in chunks]
            embeddings = await embedder.embed_async(texts)

            for chunk, embedding in zip(chunks, embeddings):
                chunk.vector_id = str(embedding.shape[0])  # placeholder
                processed += 1

            await db.commit()

    return {
        "task": "refresh_embeddings",
        "processed": processed,
        "batch_size": batch_size,
    }


async def retry_failed_ingest_jobs(ctx: dict[str, Any]) -> dict[str, Any]:
    """Retry failed ingest jobs that have not exceeded max retries.

    Args:
        ctx: Arq task context

    Returns:
        Summary dict with retried job count
    """
    from app.core.database import async_session
    from app.models.ingest_job import IngestJob
    from app.services.ingestion.service import IngestService
    from sqlalchemy import select, and_

    max_retries = 3
    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

    async with async_session() as db:
        result = await db.execute(
            select(IngestJob).where(
                and_(
                    IngestJob.status == "failed",
                    IngestJob.retry_count < max_retries,
                    IngestJob.finished_at > cutoff,
                )
            )
        )
        failed_jobs = list(result.scalars().all())

    retried = 0
    service = IngestService()

    async with async_session() as db:
        for job in failed_jobs:
            if job.source_type == "url" and job.source_input:
                try:
                    user_id = job.created_by or "system"
                    new_job = await service.ingest_url(
                        db=db,
                        url=job.source_input,
                        user_id=user_id,
                    )
                    retried += 1
                except Exception:
                    pass

    return {
        "task": "retry_failed_ingest_jobs",
        "failed_found": len(failed_jobs),
        "retried": retried,
        "max_retries": max_retries,
    }


class WorkerSettings:
    """Arq worker settings configuration.

    Usage:
        # Start worker:
        arq app.workers.arq_tasks.WorkerSettings

        # Or with CLI:
        arq worker app.workers.arq_tasks:WorkerSettings
    """

    redis_settings = RedisSettings.from_dsn("redis://localhost:6379/0")
    functions = [
        process_ingest_batch,
        cleanup_expired_sessions,
        refresh_embeddings,
        retry_failed_ingest_jobs,
    ]
    cron_jobs = [
        cron(cleanup_expired_sessions, hour=3, minute=0),  # 3 AM daily
        cron(refresh_embeddings, hour=4, minute=0),          # 4 AM daily
        cron(retry_failed_ingest_jobs, hour=5, minute=0),     # 5 AM daily
    ]
    max_jobs = 10
    keep_result = 3600  # Keep results for 1 hour
    job_timeout = 300   # 5 minute timeout per job
