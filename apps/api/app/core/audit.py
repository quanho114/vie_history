"""Structured audit logging for compliance and security monitoring.

Records all sensitive operations with who, what, when, and outcome.
Stored in PostgreSQL via bulk flush for querying.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal
import asyncio
import json

from app.core.logging import get_logger

logger = get_logger("audit")


class AuditAction(str, Enum):
    """Auditable actions in HistoriAI."""
    # Auth
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_TOKEN_REFRESH = "auth.token_refresh"
    AUTH_TOKEN_REUSE_DETECTED = "auth.token_reuse"
    # Documents
    DOCUMENT_CREATE = "document.create"
    DOCUMENT_READ = "document.read"
    DOCUMENT_UPDATE = "document.update"
    DOCUMENT_DELETE = "document.delete"
    DOCUMENT_APPROVE = "document.approve"
    DOCUMENT_REJECT = "document.reject"
    # Ingestion
    INGEST_START = "ingest.start"
    INGEST_COMPLETE = "ingest.complete"
    INGEST_FAIL = "ingest.fail"
    # Admin
    ADMIN_USER_CREATE = "admin.user_create"
    ADMIN_USER_DELETE = "admin.user_delete"
    ADMIN_USER_ROLE_CHANGE = "admin.user_role_change"
    ADMIN_SETTINGS_CHANGE = "admin.settings_change"
    # Safety
    SAFETY_PII_DETECTED = "safety.pii_detected"
    SAFETY_SSRF_BLOCKED = "safety.ssrf_blocked"
    SAFETY_ANOMALY_DETECTED = "safety.anomaly_detected"
    SAFETY_OUTPUT_FILTERED = "safety.output_filtered"
    # MCP
    MCP_TOOL_CALL = "mcp.tool_call"
    MCP_AUTH_SUCCESS = "mcp.auth_success"
    MCP_AUTH_FAILURE = "mcp.auth_failure"
    # Rate limiting
    RATE_LIMIT_EXCEEDED = "security.rate_limit_exceeded"


class AuditLevel(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class AuditEvent:
    """Structured audit event."""
    action: AuditAction
    actor_id: str | None = None
    actor_email: str | None = None
    actor_role: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    resource_type: str | None = None
    resource_id: str | None = None
    details: dict[str, Any] = field(default_factory=dict)
    outcome: Literal["success", "failure", "partial"] = "success"
    error_message: str | None = None
    risk_level: AuditLevel = AuditLevel.INFO
    session_id: str | None = None
    trace_id: str | None = None
    request_id: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "action": self.action.value,
            "actor_id": self.actor_id,
            "actor_email": self.actor_email,
            "actor_role": self.actor_role,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "details": self.details,
            "outcome": self.outcome,
            "error_message": self.error_message,
            "risk_level": self.risk_level.value,
            "session_id": self.session_id,
            "trace_id": self.trace_id,
            "request_id": self.request_id,
        }


class AuditLogger:
    """
    Async audit logger with background flush.

    Events are queued in memory and flushed to PostgreSQL periodically
    or when the queue reaches a threshold, avoiding blocking request paths.
    """

    def __init__(self, flush_interval: int = 5, batch_size: int = 50):
        self._queue: list[AuditEvent] = []
        self._flush_interval = flush_interval
        self._batch_size = batch_size
        self._flush_lock = asyncio.Lock()
        self._flush_task: asyncio.Task | None = None

    def start(self) -> None:
        """Start the background flush task."""
        if self._flush_task is None:
            self._flush_task = asyncio.create_task(self._background_flush())

    async def stop(self) -> None:
        """Stop the flush task and flush remaining events."""
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        await self._flush()

    def log(self, event: AuditEvent) -> None:
        """Queue an audit event (non-blocking)."""
        self._queue.append(event)
        if len(self._queue) >= self._batch_size:
            asyncio.create_task(self._flush())

    def log_auth_login(
        self,
        email: str,
        ip_address: str,
        success: bool,
        user_id: str | None = None,
        role: str | None = None,
        error: str | None = None,
    ) -> None:
        self.log(AuditEvent(
            action=AuditAction.AUTH_LOGIN,
            actor_id=user_id if success else None,
            actor_email=email,
            actor_role=role,
            ip_address=ip_address,
            outcome="success" if success else "failure",
            error_message=error,
            risk_level=AuditLevel.WARNING if not success else AuditLevel.INFO,
        ))

    def log_mcp_call(
        self,
        tool_name: str,
        user_id: str | None,
        ip_address: str,
        success: bool,
        error: str | None = None,
    ) -> None:
        self.log(AuditEvent(
            action=AuditAction.MCP_TOOL_CALL,
            actor_id=user_id,
            ip_address=ip_address,
            resource_type="mcp_tool",
            resource_id=tool_name,
            outcome="success" if success else "failure",
            error_message=error,
            risk_level=AuditLevel.WARNING if not success else AuditLevel.INFO,
        ))

    def log_document_access(
        self,
        action: AuditAction,
        doc_id: str,
        user_id: str,
        email: str,
        role: str,
        ip_address: str,
        success: bool = True,
    ) -> None:
        self.log(AuditEvent(
            action=action,
            actor_id=user_id,
            actor_email=email,
            actor_role=role,
            ip_address=ip_address,
            resource_type="document",
            resource_id=doc_id,
            outcome="success" if success else "failure",
            risk_level=AuditLevel.WARNING if action == AuditAction.DOCUMENT_DELETE else AuditLevel.INFO,
        ))

    def log_rate_limit_exceeded(
        self,
        ip_address: str,
        path: str,
        user_id: str | None = None,
    ) -> None:
        self.log(AuditEvent(
            action=AuditAction.RATE_LIMIT_EXCEEDED,
            actor_id=user_id,
            ip_address=ip_address,
            resource_type="endpoint",
            resource_id=path,
            outcome="failure",
            risk_level=AuditLevel.WARNING,
            details={"path": path},
        ))

    async def _flush(self) -> None:
        """Flush queued events to database."""
        if not self._queue:
            return

        async with self._flush_lock:
            if not self._queue:
                return
            events = self._queue[:self._batch_size]
            self._queue = self._queue[self._batch_size:]

        try:
            from app.core.database import async_session
            async with async_session() as db:
                from app.models.audit import AuditLog
                records = [
                    AuditLog(
                        action=e.action.value,
                        actor_id=e.actor_id,
                        actor_email=e.actor_email,
                        actor_role=e.actor_role,
                        ip_address=e.ip_address,
                        resource_type=e.resource_type,
                        resource_id=e.resource_id,
                        details=json.dumps(e.details),
                        outcome=e.outcome,
                        error_message=e.error_message,
                        risk_level=e.risk_level.value,
                        session_id=e.session_id,
                        trace_id=e.trace_id,
                        timestamp=e.timestamp,
                    )
                    for e in events
                ]
                db.add_all(records)
                await db.commit()
            logger.debug("audit_events_flushed", count=len(events))
        except Exception as exc:
            logger.error("audit_flush_failed", error=str(exc), count=len(events))
            self._queue = events + self._queue

    async def _background_flush(self) -> None:
        """Background task that flushes periodically."""
        while True:
            await asyncio.sleep(self._flush_interval)
            try:
                await self._flush()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.error("background_audit_flush_failed", error=str(exc))


# ─── Global Audit Logger ────────────────────────────────────────────────────────


_audit_logger: AuditLogger | None = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger(flush_interval=5, batch_size=50)
        _audit_logger.start()
    return _audit_logger


def audit_log(event: AuditEvent) -> None:
    """Convenience function to log an audit event."""
    get_audit_logger().log(event)
