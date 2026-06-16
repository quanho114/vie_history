"""Event bus — loose coupling between components.

Publishers emit events without knowing who consumes them.
Subscribers register handlers for events they're interested in.

Usage:
    from app.events import event_bus, DocumentIngestedEvent

    # Publishing
    await event_bus.publish(DocumentIngestedEvent(
        doc_id="123",
        url="https://...",
        title="Chiến dịch Điện Biên Phủ",
        chunk_count=42,
        status="approved",
    ))

    # Subscribing (see events/handlers.py for registered handlers)
    @event_bus.subscribe(DocumentIngestedEvent)
    async def on_document_ingested(event: DocumentIngestedEvent):
        await search_indexer.index_document(event.doc_id)
"""

from app.events.bus import DomainEvent, EventBus, event_bus

# Import handlers to register them on the event bus.
# This import must remain at the top level (not inside a function) so that
# the @event_bus.subscribe decorators run at module-load time.
from app.events import handlers as _handlers  # noqa: F401

__all__ = ["DomainEvent", "EventBus", "event_bus"]
