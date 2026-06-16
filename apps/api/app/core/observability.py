"""Observability: tracing (Langfuse), error reporting (Sentry), and metrics (Prometheus).

Langfuse integration is optional — it is only initialized when LANGFUSE_ENABLED=true
and the required env vars are set. Falls back to no-op functions gracefully.

Usage:
    from app.core.observability import trace, observe_retrieval, observe_llm_call

    with trace("query", query="Chiến dịch Điện Biên Phủ"):
        results = await query_service.hybrid_search(query)
        observe_retrieval(chunks=len(results), top_score=results[0]["rerank_score"])

The `trace` context manager works with or without Langfuse — when disabled it
is a lightweight no-op wrapper that just measures elapsed time.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Generator

import sentry_sdk

from app.core.config import settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger("observability")

# ─── Module-level state ────────────────────────────────────────────────────────

_langfuse_client: Any = None  # set by _init_langfuse()
_langfuse_available = False


# ─── Initialization ───────────────────────────────────────────────────────────

def init_observability() -> None:
    """Initialize all optional observability integrations (Sentry, Langfuse, metrics)."""
    _init_sentry()
    _init_langfuse()
    _init_metrics()
    logger.info(
        "observability_initialized",
        sentry=bool(settings.SENTRY_DSN),
        langfuse=_langfuse_available,
    )


def _init_sentry() -> None:
    if settings.SENTRY_DSN:
        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
            environment=settings.APP_ENV,
            release=settings.VERSION,
        )
        logger.info("sentry_initialized", environment=settings.APP_ENV)


def _init_langfuse() -> None:
    global _langfuse_client, _langfuse_available

    if not settings.LANGFUSE_ENABLED:
        logger.info("langfuse_disabled")
        return

    if not settings.LANGFUSE_SECRET_KEY or not settings.LANGFUSE_PUBLIC_KEY:
        logger.warning("langfuse_config_incomplete")
        return

    try:
        from langfuse import Langfuse
        _langfuse_client = Langfuse(
            secret_key=settings.LANGFUSE_SECRET_KEY,
            public_key=settings.LANGFUSE_PUBLIC_KEY,
            host=settings.LANGFUSE_HOST,
        )
        # Verify connectivity with a lightweight ping
        _langfuse_client.health_check()
        _langfuse_available = True
        logger.info("langfuse_initialized", host=settings.LANGFUSE_HOST)
    except ImportError:
        logger.warning("langfuse_import_failed")
    except Exception as exc:
        logger.warning("langfuse_init_failed", error=str(exc))


def _init_metrics() -> None:
    try:
        from app.core.metrics import init_service_info
        init_service_info(version=settings.VERSION, environment=settings.APP_ENV)
    except Exception as exc:
        logger.warning("metrics_init_failed", error=str(exc))


# ─── Tracing ─────────────────────────────────────────────────────────────────

@contextmanager
def trace(name: str, **attrs: Any) -> Generator[None, None, None]:
    """
    Lightweight tracing context manager.

    Works with or without Langfuse. When Langfuse is enabled, creates a
    Langfuse span that captures the query, retrieval results, and timing.

    Args:
        name: Span name (e.g. "hybrid_retrieval", "llm_generation")
        **attrs: Arbitrary attributes to attach to the span

    Usage:
        with trace("query", query=query_text, intent="factual"):
            results = await hybrid_search(query)
    """
    started = time.perf_counter()
    attrs_str = {k: (str(v)[:100] if isinstance(v, str) else v) for k, v in attrs.items()}

    # Start Langfuse span if available
    langfuse_span = None
    if _langfuse_available and _langfuse_client:
        try:
            langfuse_span = _langfuse_client.span(
                name=name,
                input=attrs_str,
            )
        except Exception as exc:
            logger.warning("langfuse_span_failed", error=str(exc))

    logger.debug("span_started", span=name, **attrs_str)

    try:
        yield
    except Exception as exc:
        logger.error("span_failed", span=name, error=str(exc), **attrs_str)
        if langfuse_span is not None:
            try:
                langfuse_span.update(output={"error": str(exc)})
            except Exception:
                pass
        raise
    finally:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if langfuse_span is not None:
            try:
                langfuse_span.update(
                    output={"elapsed_ms": elapsed_ms},
                    metadata={"elapsed_ms": elapsed_ms},
                )
                langfuse_span.end()
            except Exception:
                pass
        logger.debug("span_finished", span=name, elapsed_ms=elapsed_ms, **attrs_str)


class LangfuseTracer:
    """
    Higher-level Langfuse tracing wrapper for the agent pipeline.

    Wraps the full query lifecycle (classification → retrieval → synthesis)
    with Langfuse trace/span hierarchy.

    Usage:
        tracer = LangfuseTracer(session_id="session-123", user_id="user-abc")
        tracer.start(query="Chiến tranh Việt Nam")

        with tracer.span("classification", intent="factual"):
            intent = classifier.classify(query)

        with tracer.span("retrieval", top_k=5):
            results = await query_service.hybrid_search(query)

        tracer.generation(
            model=settings.ANTHROPIC_MODEL,
            prompt_tokens=500,
            completion_tokens=300,
        )
        tracer.end(answer="...")
    """

    def __init__(
        self,
        session_id: str | None = None,
        user_id: str | None = None,
        tags: list[str] | None = None,
    ):
        self.session_id = session_id
        self.user_id = user_id
        self.tags = tags or []
        self._trace: Any = None
        self._started = time.perf_counter()

    def start(self, query: str) -> None:
        """Begin a top-level Langfuse trace for the query."""
        if not _langfuse_available or not _langfuse_client:
            return
        try:
            self._trace = _langfuse_client.trace(
                name="history_query",
                session_id=self.session_id,
                user_id=self.user_id,
                input={"query": query},
                tags=self.tags + ["historiai"],
            )
            logger.info("lf_trace_started", session_id=self.session_id)
        except Exception as exc:
            logger.warning("lf_trace_start_failed", error=str(exc))
            self._trace = None

    @contextmanager
    def span(self, name: str, **input_data: Any) -> Generator[None, None, None]:
        """Create a named sub-span within the current trace."""
        started = time.perf_counter()
        lf_span = None

        if self._trace is not None:
            try:
                lf_span = self._trace.span(name=name, input=input_data)
            except Exception as exc:
                logger.warning("lf_span_failed", error=str(exc))

        try:
            yield
        except Exception as exc:
            if lf_span is not None:
                try:
                    lf_span.update(output={"error": str(exc)})
                except Exception:
                    pass
            raise
        finally:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            if lf_span is not None:
                try:
                    lf_span.update(output={"elapsed_ms": elapsed_ms})
                    lf_span.end()
                except Exception:
                    pass

    def generation(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int | None = None,
        **metadata: Any,
    ) -> None:
        """Record an LLM generation within the current trace."""
        if not _langfuse_available or not self._trace:
            return
        try:
            self._trace.generation(
                name="llm_generation",
                model=model,
                input={
                    "prompt_tokens": prompt_tokens,
                },
                output={
                    "completion_tokens": completion_tokens,
                },
                usage={
                    "input": prompt_tokens,
                    "output": completion_tokens,
                    "unit": "TOKENS",
                },
                metadata={
                    "latency_ms": latency_ms,
                    **metadata,
                },
            )
        except Exception as exc:
            logger.warning("lf_generation_failed", error=str(exc))

    def log_retrieval(
        self,
        query: str,
        chunks: list[dict[str, Any]],
        latency_ms: int,
    ) -> None:
        """Log retrieval results as a span within the trace."""
        if not _langfuse_available or not self._trace:
            return
        try:
            self._trace.span(
                name="hybrid_retrieval",
                input={"query": query},
                output={
                    "chunk_count": len(chunks),
                    "top_score": chunks[0].get("rerank_score", chunks[0].get("score", 0)) if chunks else 0,
                    "top_chunk_title": chunks[0].get("document_title", "") if chunks else None,
                },
                metadata={"latency_ms": latency_ms},
            ).end()
        except Exception as exc:
            logger.warning("lf_retrieval_log_failed", error=str(exc))

    def end(self, answer: str | None = None, **output_data: Any) -> None:
        """End the top-level trace with the final answer."""
        total_ms = int((time.perf_counter() - self._started) * 1000)
        if self._trace is not None:
            try:
                self._trace.update(
                    output={
                        "answer": (answer[:500] if answer else None),
                        "total_latency_ms": total_ms,
                        **output_data,
                    },
                    metadata={"total_latency_ms": total_ms},
                )
                self._trace.end()
                logger.info("lf_trace_ended", session_id=self.session_id, total_ms=total_ms)
            except Exception as exc:
                logger.warning("lf_trace_end_failed", error=str(exc))
        self._trace = None


# ─── Metrics helpers ──────────────────────────────────────────────────────────

def observe_retrieval(chunks: list[dict[str, Any]]) -> None:
    """Record retrieval quality metrics after a query."""
    try:
        from app.core.metrics import observe_retrieval as _observe
        if chunks:
            _observe(
                chunks=len(chunks),
                top_score=chunks[0].get("rerank_score", chunks[0].get("score", 0)),
            )
    except Exception as exc:
        logger.debug("metrics_unavailable", error=str(exc))


def observe_llm_call(
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_seconds: float,
) -> None:
    """Record LLM usage and latency metrics."""
    try:
        from app.core.metrics import observe_llm, LLM_LATENCY, LLM_ERRORS
        observe_llm(model=model, input_tokens=input_tokens, output_tokens=output_tokens)
        LLM_LATENCY.labels(model=model).observe(latency_seconds)
    except Exception as exc:
        logger.debug("metrics_unavailable", error=str(exc))
