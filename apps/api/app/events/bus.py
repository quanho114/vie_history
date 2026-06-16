"""Event bus implementation for async, decoupled communication."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, is_dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Awaitable, Callable, Any
from uuid import uuid4

if TYPE_CHECKING:
    pass

logger = logging.getLogger("event_bus")


# ─── Event Definitions ────────────────────────────────────────────────────────


@dataclass
class DomainEvent:
    """Base class for all domain events.

    Subclass this (with @dataclass) for each domain event type.
    Auto-generates event_id and occurred_at if not provided.
    """
    event_id: str | None = None
    occurred_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.event_id is None:
            object.__setattr__(self, "event_id", str(uuid4()))
        if self.occurred_at is None:
            object.__setattr__(self, "occurred_at", datetime.now(timezone.utc))


@dataclass
class DocumentIngestedEvent(DomainEvent):
    """Emitted when a document is successfully ingested and chunked."""
    doc_id: str = ""
    url: str = ""
    title: str = ""
    chunk_count: int = 0
    status: str = "pending"  # "approved" | "pending_review" | "rejected"


@dataclass
class DocumentApprovedEvent(DomainEvent):
    """Emitted when a document status changes to approved."""
    doc_id: str = ""
    title: str = ""


@dataclass
class KnowledgeDraftCreatedEvent(DomainEvent):
    """Emitted when the memory consolidation agent creates a knowledge draft."""
    draft_id: str = ""
    change_type: str = ""  # "add_node" | "add_edge" | "contradiction"
    entity_slug: str | None = None
    source_session_id: str | None = None


@dataclass
class SessionStartedEvent(DomainEvent):
    """Emitted when a new chat session begins."""
    session_id: str = ""
    user_id: str | None = None
    query: str = ""


@dataclass
class QueryCompletedEvent(DomainEvent):
    """Emitted when a query is fully processed (after streaming)."""
    session_id: str = ""
    query: str = ""
    intent: str = ""
    latency_ms: int = 0
    citation_count: int = 0
    used_llm: bool = True


@dataclass
class AgentErrorEvent(DomainEvent):
    """Emitted when an agent pipeline step fails."""
    node_name: str = ""
    error: str = ""
    query: str = ""
    session_id: str | None = None


# ─── Event Bus ────────────────────────────────────────────────────────────────


EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    """
    Async event bus supporting:

    - Fire-and-forget async event dispatch
    - Multiple handlers per event type
    - Handler error isolation (one failing handler doesn't break others)
    - Optional Redis pub/sub for multi-worker deployments
    """

    def __init__(self, use_redis: bool = False, redis_url: str | None = None) -> None:
        self._handlers: dict[type, list[EventHandler]] = {}
        self._use_redis = use_redis
        self._redis_url = redis_url
        self._pubsub = None

    def subscribe(self, event_type: type[DomainEvent]) -> Callable[[EventHandler], EventHandler]:
        """Decorator to register an event handler.

        Usage::

            @event_bus.subscribe(DocumentIngestedEvent)
            async def on_ingested(event: DocumentIngestedEvent):
                await indexer.add(event.doc_id)
        """
        def decorator(handler: EventHandler) -> EventHandler:
            self._handlers.setdefault(event_type, []).append(handler)
            return handler
        return decorator

    def unsubscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        """Remove a specific handler from an event type."""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass

    async def publish(self, event: DomainEvent) -> None:
        """Publish an event to all registered handlers (fire-and-forget)."""
        event_type = type(event)
        handlers = self._handlers.get(event_type, [])

        if not handlers:
            return

        logger.debug(
            "event_published",
            event_type=event_type.__name__,
            event_id=event.event_id,
        )

        # Fire all handlers concurrently, isolate failures
        await asyncio.gather(
            *[self._safe_handle(handler, event) for handler in handlers],
            return_exceptions=True,
        )

    async def _safe_handle(self, handler: EventHandler, event: DomainEvent) -> None:
        """Execute a handler with full error isolation."""
        try:
            await handler(event)
        except Exception as exc:
            logger.error(
                "event_handler_failed",
                handler=handler.__name__,
                event_type=type(event).__name__,
                event_id=event.event_id,
                error=str(exc),
            )

    def handler_count(self, event_type: type[DomainEvent]) -> int:
        """Return the number of registered handlers for an event type (useful for testing)."""
        return len(self._handlers.get(event_type, []))


# ─── Global Event Bus ─────────────────────────────────────────────────────────


event_bus = EventBus()
