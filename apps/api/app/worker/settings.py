"""Arq worker configuration.

Run the worker with:
    arq app.worker.settings.WorkerSettings

Or from project root:
    PYTHONPATH=. arq apps/api/app/worker/settings.py
"""

from arq import cron

from app.worker.worker import (
    RedisSettings,
    cleanup_stale_drafts,
    index_document_task,
    process_bulk_ingestion,
    process_ingestion,
    redis_settings,
)


class WorkerSettings:
    """Arq worker configuration."""

    redis_settings = redis_settings
    max_jobs = 10
    keep_result = 3600

    functions = [
        process_ingestion,
        process_bulk_ingestion,
        index_document_task,
    ]

    # Retry configuration
    max_retries = 3
    retry_delay = 60

    # Cron jobs (scheduled tasks)
    cron_jobs = [
        cron(cleanup_stale_drafts, hour=3, minute=0),  # 3 AM daily
    ]

    # Graceful shutdown
    keepalive = 65

    # Job result TTL (how long results are stored)
    result_ttl = 3600 * 24  # 24 hours
