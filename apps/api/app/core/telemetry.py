"""OpenTelemetry instrumentation for FastAPI + LangGraph.

Best practices:
- Auto-instrument FastAPI, httpx, SQLAlchemy
- Manual spans for business logic
- BatchSpanProcessor (not SimpleSpanProcessor) for production
- Semantic conventions for attribute naming

Usage:
    from app.core.telemetry import init_telemetry, telemetry_span

    # Initialize at app startup
    init_telemetry()

    # Wrap business logic
    with telemetry_span("agent.classify", {"query": query[:50]}):
        result = await classifier.classify(query)
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("telemetry")

_telemetry_available = False
_tracer = None


def init_telemetry() -> None:
    """Initialize OpenTelemetry instrumentation.

    Sets up the tracer provider with optional OTLP export for production.
    Falls back gracefully if OpenTelemetry packages are not installed.
    """
    global _telemetry_available, _tracer

    if not settings.LANGFUSE_ENABLED and not settings.SENTRY_DSN:
        logger.info("telemetry_disabled_no_provider")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.semconv.resource import ResourceAttributes

        resource = Resource.create({
            SERVICE_NAME: "historiai-api",
            SERVICE_VERSION: settings.VERSION,
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT.value: settings.APP_ENV,
        })

        provider = TracerProvider(resource=resource)

        # Console exporter for development
        if settings.APP_ENV == "development":
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        # OTLP exporter for production (requires OTEL_EXPORTER_OTLP_ENDPOINT)
        if settings.OTEL_EXPORTER_OTLP_ENDPOINT:
            try:
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
                otlp_exporter = OTLPSpanExporter(
                    endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
                    insecure=not settings.OTEL_EXPORTER_OTLP_TLS,
                )
                provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
                logger.info("otlp_exporter_configured", endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT)
            except ImportError:
                logger.warning("otlp_exporter_not_available")
            except Exception as exc:
                logger.warning("otlp_exporter_init_failed", error=str(exc))

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("historiai-api", settings.VERSION)
        _telemetry_available = True

        logger.info("telemetry_initialized", version=settings.VERSION, env=settings.APP_ENV)

    except ImportError as exc:
        logger.warning("telemetry_import_failed", error=str(exc))
    except Exception as exc:
        logger.warning("telemetry_init_failed", error=str(exc))


def init_telemetry_with_auto_instrument(app: Any = None) -> None:
    """Initialize OpenTelemetry with auto-instrumentation for FastAPI/httpx.

    Call this at app startup to enable auto-instrumentation.

    Args:
        app: FastAPI app instance (optional, for FastAPI auto-instrumentation)
    """
    global _telemetry_available, _tracer

    try:
        from opentelemetry import trace
        from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
        from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased
        from opentelemetry.semconv.resource import ResourceAttributes

        resource = Resource.create({
            SERVICE_NAME: "historiai-api",
            SERVICE_VERSION: settings.VERSION,
            ResourceAttributes.DEPLOYMENT_ENVIRONMENT.value: settings.APP_ENV,
        })

        # ParentBased sampler for distributed tracing
        # Sample 25% in production, 100% in development
        sampler = ParentBased(
            TraceIdRatioBased(0.25 if settings.APP_ENV == "production" else 1.0)
        )

        provider = TracerProvider(resource=resource, sampler=sampler)

        # Console exporter for development
        if settings.APP_ENV == "development":
            provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

        trace.set_tracer_provider(provider)
        _tracer = trace.get_tracer("historiai-api", settings.VERSION)
        _telemetry_available = True

        # Auto-instrument FastAPI
        if app is not None:
            try:
                from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
                FastAPIInstrumentor.instrument_app(
                    app,
                    excluded_urls="/health,/api/v1/health,/metrics",
                )
                logger.info("fastapi_auto_instrumented")
            except ImportError:
                logger.warning("fastapi_instrumentation_not_available")
            except Exception as exc:
                logger.warning("fastapi_instrumentation_failed", error=str(exc))

        # Auto-instrument HTTPX (for LLM calls)
        try:
            from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
            HTTPXClientInstrumentor().instrument()
            logger.info("httpx_auto_instrumented")
        except ImportError:
            logger.warning("httpx_instrumentation_not_available")
        except Exception as exc:
            logger.warning("httpx_instrumentation_failed", error=str(exc))

        logger.info("telemetry_initialized_full", version=settings.VERSION, env=settings.APP_ENV)

    except ImportError as exc:
        logger.warning("telemetry_import_failed", error=str(exc))
    except Exception as exc:
        logger.warning("telemetry_init_failed", error=str(exc))


def instrument_sqlalchemy(engine: Any) -> None:
    """Auto-instrument SQLAlchemy engine.

    Call this after engine creation.

    Args:
        engine: SQLAlchemy async engine instance
    """
    if not _telemetry_available:
        return

    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("sqlalchemy_auto_instrumented")
    except ImportError:
        logger.warning("sqlalchemy_instrumentation_not_available")
    except Exception as exc:
        logger.warning("sqlalchemy_instrumentation_failed", error=str(exc))


@contextmanager
def telemetry_span(
    name: str,
    attributes: dict[str, Any] | None = None,
):
    """Context manager for creating OpenTelemetry spans.

    Usage:
        with telemetry_span("agent.classify", {"query": query[:50]}):
            result = await classifier.classify(query)
    """
    global _telemetry_available, _tracer

    if not _telemetry_available or _tracer is None:
        yield
        return

    try:

        with _tracer.start_as_current_span(name) as span:
            if attributes:
                for k, v in attributes.items():
                    if v is not None:
                        span.set_attribute(k, str(v)[:200])
            yield span
    except Exception as exc:
        logger.warning("telemetry_span_failed", span=name, error=str(exc))
        yield


def record_metric(
    metric_name: str,
    value: float,
    unit: str = "",
    attributes: dict[str, str] | None = None,
) -> None:
    """Record a metric to OpenTelemetry + Prometheus.

    For now, records to Prometheus (which is already set up).
    OpenTelemetry metrics can be added once OTLP endpoint is configured.
    """
    try:
        from app.core.metrics import LLM_LATENCY, observe_llm
        # Route to appropriate metric
        if "latency" in metric_name.lower():
            LLM_LATENCY.labels(
                model=attributes.get("model", "unknown") if attributes else "unknown"
            ).observe(value)
        else:
            observe_llm(
                model=attributes.get("model", "unknown") if attributes else "unknown",
                input_tokens=int(attributes.get("input_tokens", 0)) if attributes else 0,
                output_tokens=int(attributes.get("output_tokens", 0)) if attributes else 0,
            )
    except Exception as exc:
        logger.debug("metric_record_failed", error=str(exc))


def get_current_trace_context() -> dict[str, str] | None:
    """Get the current trace context (trace_id, span_id) for logging correlation.

    Returns:
        Dict with trace_id and span_id if a span is active, None otherwise.
    """
    if not _telemetry_available:
        return None

    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        if span and span.is_recording():
            ctx = span.get_span_context()
            return {
                "trace_id": format(ctx.trace_id, "032x"),
                "span_id": format(ctx.span_id, "016x"),
            }
    except Exception:
        pass
    return None
