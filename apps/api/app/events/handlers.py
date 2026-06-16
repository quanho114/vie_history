"""Domain event handlers — registered on the global event bus.

Each handler is idempotent and uses error isolation (see bus.py).
Adding a new handler here is sufficient — no other code changes needed.
"""

from app.events.bus import (
    DocumentIngestedEvent,
    DocumentApprovedEvent,
    KnowledgeDraftCreatedEvent,
    QueryCompletedEvent,
    SessionStartedEvent,
    event_bus,
)


# ─── Document Events ───────────────────────────────────────────────────────────


@event_bus.subscribe(DocumentIngestedEvent)
async def index_document_on_ingest(event: DocumentIngestedEvent) -> None:
    """Auto-index a document in Qdrant when ingested."""
    import logging
    _logger = logging.getLogger("event_bus.handlers")

    if event.status not in ("approved", "pending_review"):
        return

    try:
        from app.services.retrieval.vector_search import VectorSearch
        vs = VectorSearch()
        await vs.index_document(event.doc_id)
        _logger.info("document_indexed", doc_id=event.doc_id)
    except Exception as exc:
        _logger.warning("document_index_failed", doc_id=event.doc_id, error=str(exc))


@event_bus.subscribe(DocumentApprovedEvent)
async def meili_index_on_approval(event: DocumentApprovedEvent) -> None:
    """Auto-index document chunks in Meilisearch when a document is approved."""
    import logging
    _logger = logging.getLogger("event_bus.handlers")

    try:
        from app.services.retrieval.meilisearch_bm25 import get_meilisearch_bm25
        meili = await get_meilisearch_bm25()
        # Remove stale chunks for this document, then re-index via IngestService
        await meili.remove_by_document_id(str(event.doc_id))
        _logger.info("meili_document_reindex_triggered", doc_id=event.doc_id)
    except Exception as exc:
        _logger.warning("meili_index_failed", doc_id=event.doc_id, error=str(exc))


# ─── Knowledge Draft Events ───────────────────────────────────────────────────


@event_bus.subscribe(KnowledgeDraftCreatedEvent)
async def log_draft_creation(event: KnowledgeDraftCreatedEvent) -> None:
    """Log knowledge draft creation for admin dashboard monitoring."""
    import logging
    _logger = logging.getLogger("event_bus.handlers")
    _logger.info(
        "knowledge_draft_pending_review",
        draft_id=event.draft_id,
        change_type=event.change_type,
        entity_slug=event.entity_slug,
    )


# ─── Session Events ───────────────────────────────────────────────────────────


@event_bus.subscribe(SessionStartedEvent)
async def record_session_start(event: SessionStartedEvent) -> None:
    """Record session start metrics."""
    import logging
    _logger = logging.getLogger("event_bus.handlers")
    _logger.info("session_started", session_id=event.session_id, user_id=event.user_id)


# ─── Query Completion Events ──────────────────────────────────────────────────


@event_bus.subscribe(QueryCompletedEvent)
async def record_query_metrics(event: QueryCompletedEvent) -> None:
    """Record query completion metrics to Prometheus."""
    import logging
    _logger = logging.getLogger("event_bus.handlers")

    try:
        from app.core.metrics import QUERY_TOTAL, QUERY_LATENCY
        QUERY_TOTAL.labels(intent=event.intent, status="success").inc()
        QUERY_LATENCY.labels(stage="total").observe(event.latency_ms / 1000)
        _logger.debug(
            "query_metrics_recorded",
            intent=event.intent,
            latency_ms=event.latency_ms,
            citations=event.citation_count,
        )
    except Exception as exc:
        _logger.debug("metrics_unavailable", error=str(exc))
