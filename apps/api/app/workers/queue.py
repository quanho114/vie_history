"""Queue helpers for background jobs."""

from redis import Redis
from rq import Queue

from app.core.config import settings


def get_ingest_queue() -> Queue:
    """Return the configured ingestion queue."""
    connection = Redis.from_url(settings.REDIS_URL)
    return Queue(settings.RQ_QUEUE_NAME, connection=connection)
