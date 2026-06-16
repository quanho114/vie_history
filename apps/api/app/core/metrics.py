"""Prometheus metrics for HistoriAI Agent.

Tracks query latency, retrieval quality, ingestion throughput,
LLM token usage, and system health.

Usage:
    from app.core.metrics import QUERY_TOTAL, QUERY_LATENCY, observe_retrieval

    QUERY_TOTAL.labels(intent="factual", status="success").inc()
    QUERY_LATENCY.labels(stage="retrieval").observe(0.234)
    observe_retrieval(chunks=5, top_score=0.87)
"""

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, Info

# Create a custom registry so metrics can be registered conditionally
_registry: CollectorRegistry | None = None


def _get_registry() -> CollectorRegistry:
    global _registry
    if _registry is None:
        from prometheus_client import REGISTRY
        _registry = REGISTRY
    return _registry


# ─── Query metrics ────────────────────────────────────────────────────────────

QUERY_TOTAL = Counter(
    "historiai_queries_total",
    "Total queries processed",
    ["intent", "status"],
    registry=_get_registry(),
)

QUERY_LATENCY = Histogram(
    "historiai_query_latency_seconds",
    "Query latency in seconds by stage",
    ["stage"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0),
    registry=_get_registry(),
)

QUERY_INPUT_TOKENS = Histogram(
    "historiai_query_input_tokens",
    "Input token count per query",
    ["model"],
    buckets=(100, 250, 500, 1000, 2000, 4000, 8000),
    registry=_get_registry(),
)

QUERY_OUTPUT_TOKENS = Histogram(
    "historiai_query_output_tokens",
    "Output token count per query",
    ["model"],
    buckets=(50, 100, 250, 500, 1000, 2000, 4000),
    registry=_get_registry(),
)

# ─── Retrieval metrics ───────────────────────────────────────────────────────

RETRIEVAL_CHUNKS = Histogram(
    "historiai_retrieval_chunks_retrieved",
    "Number of chunks retrieved per query",
    buckets=(1, 3, 5, 8, 10, 15, 20, 30),
    registry=_get_registry(),
)

RETRIEVAL_TOP_SCORE = Histogram(
    "historiai_retrieval_top_score",
    "Top retrieval relevance score after reranking",
    buckets=(0.1, 0.3, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0),
    registry=_get_registry(),
)

RETRIEVAL_STAGE_LATENCY = Histogram(
    "historiai_retrieval_stage_latency_seconds",
    "Latency of each retrieval stage",
    ["stage"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0),
    registry=_get_registry(),
)

BM25_INDEX_SIZE = Gauge(
    "historiai_bm25_index_size",
    "Number of documents in the BM25 index",
    registry=_get_registry(),
)

ES_INDEX_SIZE = Gauge(
    "historiai_es_index_size",
    "Number of documents in Elasticsearch BM25 index",
    registry=_get_registry(),
)

VECTOR_COLLECTION_SIZE = Gauge(
    "historiai_vector_collection_size",
    "Number of vectors in Qdrant collection",
    registry=_get_registry(),
)

# ─── Ingestion metrics ────────────────────────────────────────────────────────

DOCUMENTS_INGESTED = Counter(
    "historiai_documents_ingested_total",
    "Total documents ingested",
    ["status", "source_type"],
    registry=_get_registry(),
)

DOCUMENTS_FAILED = Counter(
    "historiai_documents_failed_total",
    "Total documents that failed ingestion",
    ["stage"],
    registry=_get_registry(),
)

CHUNKS_INDEXED = Counter(
    "historiai_chunks_indexed_total",
    "Total chunks indexed",
    ["target"],
    registry=_get_registry(),
)

INGEST_LATENCY = Histogram(
    "historiai_ingest_latency_seconds",
    "Total ingestion pipeline latency",
    ["stage"],
    buckets=(1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
    registry=_get_registry(),
)

# ─── LLM metrics ─────────────────────────────────────────────────────────────

LLM_TOKENS = Counter(
    "historiai_llm_tokens_total",
    "Total LLM tokens consumed",
    ["model", "type"],
    registry=_get_registry(),
)

LLM_LATENCY = Histogram(
    "historiai_llm_latency_seconds",
    "LLM API call latency",
    ["model"],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 60.0),
    registry=_get_registry(),
)

LLM_ERRORS = Counter(
    "historiai_llm_errors_total",
    "Total LLM API errors",
    ["model", "error_type"],
    registry=_get_registry(),
)

# ─── Agent Safety metrics ─────────────────────────────────────────────────────

AGENT_SESSIONS_ACTIVE = Gauge(
    "historiai_agent_sessions_active",
    "Number of active agent sessions",
    registry=_get_registry(),
)

AGENT_ABORTS_TOTAL = Counter(
    "historiai_agent_aborts_total",
    "Total agent session aborts",
    ["reason"],
    registry=_get_registry(),
)

AGENT_TOKEN_BUDGET_EXCEEDED = Counter(
    "historiai_agent_token_budget_exceeded_total",
    "Total times token budget was exceeded",
    registry=_get_registry(),
)

AGENT_LOOPS_DETECTED = Counter(
    "historiai_agent_loops_detected_total",
    "Total loops detected and prevented",
    registry=_get_registry(),
)

AGENT_COST_USD = Counter(
    "historiai_agent_cost_usd_total",
    "Total estimated cost in USD",
    ["session_id"],
    registry=_get_registry(),
)

AGENT_APPROVALS_REQUESTED = Counter(
    "historiai_agent_approvals_requested_total",
    "Total human-in-the-loop approvals requested",
    ["status"],  # pending, approved, denied
    registry=_get_registry(),
)

AGENT_TOOL_CALLS_TOTAL = Counter(
    "historiai_agent_tool_calls_total",
    "Total tool calls made by agents",
    ["tool_name", "status"],
    registry=_get_registry(),
)

AGENT_CHECKPOINTS_CREATED = Counter(
    "historiai_agent_checkpoints_created_total",
    "Total checkpoints created for agent recovery",
    registry=_get_registry(),
)

# ─── HTTP Request metrics (Phase 2 enhancements) ─────────────────────────────

REQUEST_LATENCY = Histogram(
    "historiai_http_request_duration_seconds",
    "HTTP request latency by endpoint and method",
    ["method", "endpoint", "status_code"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=_get_registry(),
)

# ─── Retrieval quality metrics (Phase 2 enhancements) ─────────────────────────

RETRIEVAL_QUALITY = Histogram(
    "historiai_retrieval_quality_score",
    "Retrieval quality score (0-1) from reranker",
    ["reranker_type"],
    buckets=(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
    registry=_get_registry(),
)

# ─── Cache metrics (Phase 2 enhancements) ───────────────────────────────────

CACHE_OPERATIONS = Counter(
    "historiai_cache_operations_total",
    "Cache get/set operations",
    ["operation", "result"],  # result: hit, miss, error
    registry=_get_registry(),
)

# ─── Agent step metrics (Phase 2 enhancements) ──────────────────────────────

AGENT_STEP_DURATION = Histogram(
    "historiai_agent_step_duration_seconds",
    "Duration of each agent pipeline step",
    ["step_name", "mode"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0),
    registry=_get_registry(),
)

# ─── System health ────────────────────────────────────────────────────────────

KB_CHUNKS_TOTAL = Gauge(
    "historiai_kb_chunks_total",
    "Total chunks in the knowledge base (PostgreSQL source of truth)",
    registry=_get_registry(),
)

CACHE_HIT_RATIO = Gauge(
    "historiai_cache_hit_ratio",
    "Redis cache hit ratio (updated on each cache lookup)",
    registry=_get_registry(),
)

SERVICE_INFO = Info(
    "historiai_service",
    "HistoriAI service metadata",
    registry=_get_registry(),
)


# ─── Convenience helpers ──────────────────────────────────────────────────────

def observe_retrieval(chunks: int, top_score: float) -> None:
    """Record retrieval quality metrics after a query."""
    RETRIEVAL_CHUNKS.observe(chunks)
    if chunks > 0:
        RETRIEVAL_TOP_SCORE.observe(top_score)


def observe_llm(model: str, input_tokens: int, output_tokens: int) -> None:
    """Record LLM token usage."""
    LLM_TOKENS.labels(model=model, type="input").inc(input_tokens)
    LLM_TOKENS.labels(model=model, type="output").inc(output_tokens)
    QUERY_INPUT_TOKENS.labels(model=model).observe(input_tokens)
    QUERY_OUTPUT_TOKENS.labels(model=model).observe(output_tokens)


def record_ingestion(status: str, source_type: str, chunks: int = 0, target: str = "vector") -> None:
    """Record ingestion outcome."""
    if status == "success":
        DOCUMENTS_INGESTED.labels(status="success", source_type=source_type).inc()
        if chunks > 0:
            CHUNKS_INDEXED.labels(target=target).inc(chunks)
    else:
        DOCUMENTS_FAILED.labels(stage=status).inc()


def init_service_info(version: str, environment: str) -> None:
    """Set static service metadata."""
    SERVICE_INFO.info({
        "version": version,
        "environment": environment,
    })


def observe_http_request(method: str, endpoint: str, status_code: int, latency: float) -> None:
    """Record HTTP request latency by endpoint and method."""
    REQUEST_LATENCY.labels(
        method=method,
        endpoint=endpoint,
        status_code=str(status_code),
    ).observe(latency)


def observe_cache_operation(operation: str, result: str) -> None:
    """Record cache hit/miss operations.

    Args:
        operation: "get" or "set"
        result: "hit", "miss", or "error"
    """
    CACHE_OPERATIONS.labels(operation=operation, result=result).inc()


def observe_agent_step(step_name: str, mode: str, duration: float) -> None:
    """Record agent pipeline step duration.

    Args:
        step_name: Name of the step (e.g., "classification", "retrieval", "generation")
        mode: Agent mode (e.g., "factual", "narrative", "exploratory")
        duration: Duration in seconds
    """
    AGENT_STEP_DURATION.labels(step_name=step_name, mode=mode).observe(duration)


def observe_retrieval_quality(reranker_type: str, quality_score: float) -> None:
    """Record retrieval quality score from reranker.

    Args:
        reranker_type: Type of reranker used (e.g., "cross_encoder", "bm25")
        quality_score: Quality score between 0 and 1
    """
    RETRIEVAL_QUALITY.labels(reranker_type=reranker_type).observe(quality_score)
