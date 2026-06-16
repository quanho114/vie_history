"""Structured JSON Logging with Request Context."""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog

from app.core.config import settings


# === CONTEXT VAR ===
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
session_id_var: ContextVar[str] = ContextVar("session_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
job_id_var: ContextVar[str] = ContextVar("job_id", default="")


def set_request_context(
    request_id: str | None = None,
    session_id: str | None = None,
    user_id: str | None = None,
    job_id: str | None = None,
) -> None:
    """Set context variables for logging."""
    if request_id:
        request_id_var.set(request_id)
    if session_id:
        session_id_var.set(session_id)
    if user_id:
        user_id_var.set(user_id)
    if job_id:
        job_id_var.set(job_id)


def get_request_id() -> str:
    """Get current request ID."""
    return request_id_var.get()


def generate_request_id() -> str:
    """Generate new request ID."""
    rid = str(uuid.uuid4())[:8]
    request_id_var.set(rid)
    return rid


# === STRUCTLOG CONFIGURATION ===
def add_context(logger, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
    """Add context fields to every log entry."""
    event_dict["request_id"] = request_id_var.get()
    event_dict["session_id"] = session_id_var.get()
    event_dict["user_id"] = user_id_var.get()
    event_dict["job_id"] = job_id_var.get()

    # Remove empty context values
    return {k: v for k, v in event_dict.items() if v}


def configure_logging() -> None:
    """Configure structured logging."""

    # Determine processors based on environment
    if settings.is_production:
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.UnicodeDecoder(),
            structlog.processors.format_exc_info,
            add_context,
            structlog.processors.JSONRenderer(),
        ]
    else:
        processors = [
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="%H:%M:%S"),
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            add_context,
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.LOG_LEVEL),
    )

    # Reduce noise from third-party libraries
    for logger_name in ["uvicorn", "uvicorn.access", "httpx", "httpcore"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


# === LOGGER ===
def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get structured logger."""
    return structlog.get_logger(name)


# === CONVENIENCE LOGGER ===
logger = get_logger("historiai")
