"""Background queue manager for sequential ingestion."""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from app.core.database import async_session
from app.models.ingest_job import IngestJob
from app.models.user import User
from app.core.logging import get_logger

logger = get_logger("ingestion_queue")


class IngestionQueueManager:
    """Manages sequential background processing of document ingestion jobs."""

    def __init__(self) -> None:
        self.queue: asyncio.Queue[str] = asyncio.Queue()
        self.worker_task: Optional[asyncio.Task] = None
        self.job_params: Dict[str, Dict[str, Any]] = {}
        self._running: bool = False

    async def start(self) -> None:
        """Start the background worker and load queued/running jobs from DB."""
        if self._running:
            return
        self._running = True
        self.worker_task = asyncio.create_task(self._worker())
        logger.info("ingestion_queue_worker_started")

        # Load pending jobs from DB that were queued or running (which were interrupted)
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(IngestJob)
                    .where(IngestJob.status.in_(["queued", "running"]))
                    .order_by(IngestJob.created_at.asc())
                )
                jobs = result.scalars().all()
                for job in jobs:
                    # Reset running jobs to queued since they were interrupted
                    if job.status == "running":
                        job.status = "queued"
                        job.stage = "queued"
                        job.add_log("Job reset to queued due to system restart")
                    
                    logger.info("re_queuing_job_on_startup", job_id=job.id, status=job.status)
                    await self.queue.put(job.id)
                await db.commit()
        except Exception as e:
            logger.error("error_loading_queued_jobs_on_startup", error=str(e))

    async def stop(self) -> None:
        """Stop the background worker."""
        self._running = False
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass
            self.worker_task = None
        logger.info("ingestion_queue_worker_stopped")

    async def add_job(
        self,
        job_id: str,
        user_id: str,
        tags: Optional[List[str]] = None,
        file_path: Optional[str] = None,
        content_type: Optional[str] = None,
    ) -> None:
        """Queue a job for sequential processing."""
        self.job_params[job_id] = {
            "user_id": user_id,
            "tags": tags,
            "file_path": file_path,
            "content_type": content_type,
        }
        await self.queue.put(job_id)
        logger.info("job_queued", job_id=job_id)

    async def _worker(self) -> None:
        # Allow the API and embedding models to fully warm up on startup before starting ingestion
        await asyncio.sleep(5)
        logger.info("ingestion_queue_worker_started_processing")
        while self._running:
            try:
                job_id = await self.queue.get()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("queue_get_error", error=str(e))
                await asyncio.sleep(1)
                continue

            try:
                await self._process_job(job_id)
            except Exception as e:
                logger.exception("job_processing_exception", job_id=job_id, error=str(e))
            finally:
                self.queue.task_done()
                self.job_params.pop(job_id, None)

    async def _process_job(self, job_id: str) -> None:
        logger.info("processing_job", job_id=job_id)

        # Get custom parameters if available
        params = self.job_params.get(job_id, {})
        user_id = params.get("user_id")
        tags = params.get("tags")
        file_path_str = params.get("file_path")
        content_type = params.get("content_type")

        async with async_session() as db:
            # Fetch job details
            result = await db.execute(
                select(IngestJob).where(IngestJob.id == job_id)
            )
            job = result.scalar_one_or_none()
            if not job:
                logger.warning("job_not_found", job_id=job_id)
                return

            if job.status not in ("queued", "running"):
                logger.info("job_already_processed", job_id=job_id, status=job.status)
                return

            # Fallback for user_id on system recovery/restart
            if not user_id:
                user_result = await db.execute(select(User).limit(1))
                fallback_user = user_result.scalar_one_or_none()
                if fallback_user:
                    user_id = fallback_user.id
                else:
                    user_id = "00000000-0000-0000-0000-000000000000"

            # Use IngestService to run the ingestion
            from app.services.ingestion.service import IngestService
            ingest_service = IngestService()

            # Update job state in DB to running
            job.status = "running"
            job.started_at = datetime.now(timezone.utc)
            job.add_log("Job picked up by background queue worker")
            await db.commit()

            try:
                if job.source_type == "url":
                    await ingest_service.ingest_url(
                        db=db,
                        url=job.source_input,
                        user_id=user_id,
                        tags=tags,
                        job_id=job_id,
                    )
                elif job.source_type == "file":
                    if file_path_str:
                        file_path = Path(file_path_str)
                    else:
                        file_path = Path("storage/uploads") / job.source_input

                    await ingest_service.ingest_file(
                        db=db,
                        file_path=file_path,
                        filename=job.source_input,
                        user_id=user_id,
                        content_type=content_type,
                        tags=tags,
                        job_id=job_id,
                    )
                else:
                    job.status = "failed"
                    job.stage = "queued"
                    job.error_message = f"Unsupported source type: {job.source_type}"
                    job.finished_at = datetime.now(timezone.utc)
                    job.add_log(job.error_message, "error")
                    await db.commit()
            except Exception as e:
                logger.exception("job_execution_failed", job_id=job_id, error=str(e))
                job.status = "failed"
                job.stage = "unexpected_error"
                job.error_message = str(e)
                job.finished_at = datetime.now(timezone.utc)
                job.add_log(str(e), "error")
                await db.commit()


# Global singleton instance
ingestion_queue_manager = IngestionQueueManager()
