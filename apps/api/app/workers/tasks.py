"""RQ-compatible ingestion tasks."""

import asyncio

from app.core.database import get_db_context
from app.models.ingest_job import IngestJob
from app.services.ingestion.service import IngestService


async def _run_retry(job_id: str, user_id: str) -> str:
    async with get_db_context() as db:
        job = await db.get(IngestJob, job_id)
        if job is None:
            raise ValueError(f"Ingest job not found: {job_id}")
        retried = await IngestService().retry_job(db=db, job=job, user_id=user_id)
        return retried.id


def retry_ingest_job(job_id: str, user_id: str) -> str:
    """Retry an ingestion job from an RQ worker."""
    return asyncio.run(_run_retry(job_id=job_id, user_id=user_id))
