"""Background worker module for Arq task queue.

Arq is preferred over RQ because it natively supports async/await,
integrates cleanly with FastAPI's async ecosystem, and uses
Pydantic for job result serialization.

Run the worker:
    arq app.worker.settings.WorkerSettings

Tasks:
- process_ingestion: Background URL ingestion
- process_bulk_ingestion: Bulk URL ingestion
- index_document_task: Index document in Qdrant/Elasticsearch
- cleanup_stale_drafts: Daily cleanup of stale drafts
"""

from app.worker.settings import WorkerSettings

__all__ = ["WorkerSettings"]
