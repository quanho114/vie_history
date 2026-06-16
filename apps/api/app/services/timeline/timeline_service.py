"""Timeline service — CRUD + LLM-based event extraction."""

from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.timeline import HistoricalEvent
from app.models.wiki import WikiPage
from app.services.llm.client import get_llm_client
from app.services.llm.json_parser import parse_llm_json

logger = get_logger("timeline_service")

# ---------------------------------------------------------------------------
# LLM system prompt for event extraction
# ---------------------------------------------------------------------------

_EXTRACT_SYSTEM_PROMPT = (
    "You are a Vietnamese history expert. "
    "Extract historical events from the document provided. "
    "Return a JSON array of events — no markdown fences, no extra text. "
    "Each event object MUST have these fields:\n"
    "  event_name (string),\n"
    "  slug (URL-friendly string, lowercase, hyphens only),\n"
    "  summary (string, 1-3 sentences),\n"
    "  start_year (integer or null),\n"
    "  end_year (integer or null),\n"
    "  period (one of: khang_chien_chong_phap | khang_chien_chong_my | thong_nhat | khac),\n"
    "  importance_level (integer 1-5),\n"
    "  event_type (one of: battle | treaty | political | cultural | economic | other),\n"
    "  causes (array of strings),\n"
    "  effects (array of strings),\n"
    "  people_involved (array of strings),\n"
    "  locations (array of strings)."
)


def _slugify(text: str) -> str:
    """Very light Vietnamese-safe slugifier (ASCII fallback)."""
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug, flags=re.UNICODE)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug[:490]


def _as_list(value: Any) -> list[str]:
    """Normalize LLM/wiki content values into a list of strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def _safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


class TimelineService:
    """Business logic for historical event management."""

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------

    async def get_events(
        self,
        db: AsyncSession,
        *,
        period: str | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        event_type: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[HistoricalEvent], int]:
        """Return a paginated, filtered list of historical events.

        Returns:
            (events, total_count) tuple.
        """
        base_query = select(HistoricalEvent).options(selectinload(HistoricalEvent.wiki_page))
        count_query = select(func.count(HistoricalEvent.id))

        filters = []
        if period:
            filters.append(HistoricalEvent.period == period)
        if event_type:
            filters.append(HistoricalEvent.event_type == event_type)
        if start_year is not None:
            filters.append(HistoricalEvent.start_year >= start_year)
        if end_year is not None:
            # Include events that started before or during end_year
            filters.append(
                or_(
                    HistoricalEvent.end_year <= end_year,
                    HistoricalEvent.start_year <= end_year,
                )
            )
        if search:
            pattern = f"%{search}%"
            filters.append(
                or_(
                    HistoricalEvent.event_name.ilike(pattern),
                    HistoricalEvent.summary.ilike(pattern),
                )
            )

        for f in filters:
            base_query = base_query.where(f)
            count_query = count_query.where(f)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        result = await db.execute(
            base_query.order_by(
                HistoricalEvent.start_year.asc().nullslast(),
                HistoricalEvent.importance_level.desc(),
            )
            .offset(offset)
            .limit(page_size)
        )
        events = list(result.scalars().all())

        return events, total

    async def get_event_by_slug(
        self,
        db: AsyncSession,
        slug: str,
    ) -> HistoricalEvent | None:
        """Fetch a single event by its URL slug."""
        result = await db.execute(
            select(HistoricalEvent)
            .options(selectinload(HistoricalEvent.wiki_page))
            .where(HistoricalEvent.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_event_by_id(
        self,
        db: AsyncSession,
        event_id: str,
    ) -> HistoricalEvent | None:
        """Fetch a single event by its UUID."""
        result = await db.execute(
            select(HistoricalEvent)
            .options(selectinload(HistoricalEvent.wiki_page))
            .where(HistoricalEvent.id == event_id)
        )
        return result.scalar_one_or_none()

    async def _upsert_event(
        self,
        db: AsyncSession,
        data: dict[str, Any],
    ) -> HistoricalEvent:
        """Create or update an event matched by slug."""
        slug = data.get("slug") or _slugify(data.get("event_name", "event"))
        data["slug"] = slug

        existing = await self.get_event_by_slug(db, slug)
        if existing is None:
            return await self.create_event(db, data)

        for key, value in data.items():
            if value is not None:
                setattr(existing, key, value)
        await db.flush()
        await db.refresh(existing)
        logger.info("historical_event_upserted", event_id=existing.id, slug=slug)
        return existing

    async def create_event(
        self,
        db: AsyncSession,
        data: dict[str, Any],
    ) -> HistoricalEvent:
        """Persist a new historical event.

        Auto-generates slug from event_name if not provided.
        """
        if not data.get("slug") and data.get("event_name"):
            data["slug"] = _slugify(data["event_name"])

        event = HistoricalEvent(**data)
        db.add(event)
        await db.flush()
        await db.refresh(event)
        logger.info("historical_event_created", event_id=event.id, slug=event.slug)
        return event

    async def update_event(
        self,
        db: AsyncSession,
        event_id: str,
        data: dict[str, Any],
    ) -> HistoricalEvent:
        """Update an existing event (partial update — only non-None keys applied).

        Raises:
            ValueError: if the event does not exist.
        """
        event = await self.get_event_by_id(db, event_id)
        if event is None:
            raise ValueError(f"HistoricalEvent not found: {event_id}")

        for key, value in data.items():
            if value is not None:
                setattr(event, key, value)

        await db.flush()
        await db.refresh(event)
        logger.info("historical_event_updated", event_id=event.id)
        return event

    async def delete_event(self, db: AsyncSession, event_id: str) -> None:
        """Delete an event by its UUID.

        Raises:
            ValueError: if the event does not exist.
        """
        event = await self.get_event_by_id(db, event_id)
        if event is None:
            raise ValueError(f"HistoricalEvent not found: {event_id}")

        await db.delete(event)
        await db.flush()
        logger.info("historical_event_deleted", event_id=event_id)

    # ------------------------------------------------------------------
    # LLM-based extraction
    # ------------------------------------------------------------------

    async def extract_events_from_document(
        self,
        db: AsyncSession,
        document_id: str,
    ) -> list[HistoricalEvent]:
        """Load a document's markdown content, call LLM, persist extracted events.

        Raises:
            ValueError: if the document is not found or has no markdown content.
        """
        from app.models.document import Document

        doc_result = await db.execute(
            select(Document).where(Document.id == document_id)
        )
        document = doc_result.scalar_one_or_none()
        if document is None:
            raise ValueError(f"Document not found: {document_id}")

        if not document.markdown_content_path:
            raise ValueError(
                f"Document {document_id} has no markdown_content_path set."
            )

        # Read the on-disk markdown content
        try:
            import aiofiles  # type: ignore[import]

            async with aiofiles.open(
                document.markdown_content_path, encoding="utf-8"
            ) as fh:
                content = await fh.read()
        except OSError as exc:
            raise ValueError(
                f"Cannot read markdown content for document {document_id}: {exc}"
            ) from exc

        # Truncate to ~12 000 chars to stay within typical context windows
        content_snippet = content[:12_000]

        prompt = (
            f"Document title: {document.title}\n\n"
            f"Content:\n{content_snippet}\n\n"
            "Extract all significant historical events from this document and "
            "return them as a JSON array."
        )

        llm = get_llm_client()
        logger.info(
            "timeline_extraction_started",
            document_id=document_id,
            content_length=len(content_snippet),
        )
        raw_response = await llm.generate(
            prompt,
            system=_EXTRACT_SYSTEM_PROMPT,
            max_tokens=4096,
        )

        # Parse JSON — use shared parser that handles markdown fences and conversational prefixes
        try:
            events_data: list[dict] = parse_llm_json(raw_response)
        except (ValueError, json.JSONDecodeError) as exc:
            logger.error(
                "timeline_extraction_json_error",
                document_id=document_id,
                error=str(exc),
                raw=raw_response[:500],
            )
            raise ValueError(f"LLM returned invalid JSON: {exc}") from exc

        created_events: list[HistoricalEvent] = []
        for item in events_data:
            event_payload = {
                "event_name": item.get("event_name", "Unknown Event"),
                "slug": item.get("slug") or _slugify(item.get("event_name", "event")),
                "summary": item.get("summary"),
                "start_year": item.get("start_year"),
                "end_year": item.get("end_year"),
                "period": item.get("period"),
                "importance_level": max(1, min(5, int(item.get("importance_level", 1)))),
                "event_type": item.get("event_type"),
                "causes": item.get("causes") or [],
                "effects": item.get("effects") or [],
                "people_involved": item.get("people_involved") or [],
                "locations": item.get("locations") or [],
                "source_document_ids": [document_id],
            }
            event = await self._upsert_event(db, event_payload)
            created_events.append(event)

        logger.info(
            "timeline_extraction_done",
            document_id=document_id,
            events_created=len(created_events),
        )
        return created_events

    async def extract_events_from_wiki_page(
        self,
        db: AsyncSession,
        wiki_page_id: str,
    ) -> list[HistoricalEvent]:
        """Extract or derive timeline events from a committed WikiPage."""
        page_result = await db.execute(select(WikiPage).where(WikiPage.id == wiki_page_id))
        page = page_result.scalar_one_or_none()
        if page is None:
            raise ValueError(f"WikiPage not found: {wiki_page_id}")

        events_data = self._events_from_structured_wiki_content(page)
        if not events_data:
            events_data = await self._events_from_wiki_llm(page)

        created_events: list[HistoricalEvent] = []
        for item in events_data:
            event_name = item.get("event_name") or item.get("title") or page.title
            event_payload = {
                "event_name": event_name,
                "slug": item.get("slug") or (page.slug if event_name == page.title else _slugify(event_name)),
                "summary": item.get("summary") or page.summary,
                "start_year": _safe_int(item.get("start_year"), page.start_year),
                "end_year": _safe_int(item.get("end_year"), page.end_year),
                "period": item.get("period") or page.period,
                "importance_level": max(1, min(5, _safe_int(item.get("importance_level"), 3) or 3)),
                "event_type": item.get("event_type") or page.event_type or "other",
                "causes": _as_list(item.get("causes") or (page.content or {}).get("causes")),
                "effects": _as_list(item.get("effects") or (page.content or {}).get("results")),
                "people_involved": _as_list(item.get("people_involved") or (page.content or {}).get("people")),
                "locations": _as_list(item.get("locations")),
                "wiki_page_id": page.id,
                "source_document_ids": page.source_document_ids,
                "metadata_json": {"source": "wiki_pipeline", "wiki_page_slug": page.slug},
            }
            created_events.append(await self._upsert_event(db, event_payload))

        logger.info(
            "wiki_timeline_extraction_done",
            wiki_page_id=wiki_page_id,
            events_created=len(created_events),
        )
        return created_events

    def _events_from_structured_wiki_content(self, page: WikiPage) -> list[dict[str, Any]]:
        content = page.content or {}
        raw_timeline = content.get("timeline") if isinstance(content, dict) else None
        events: list[dict[str, Any]] = []

        if isinstance(raw_timeline, list):
            for item in raw_timeline:
                if isinstance(item, dict):
                    title = item.get("event_name") or item.get("title") or item.get("event") or page.title
                    events.append(
                        {
                            "event_name": title,
                            "slug": item.get("slug"),
                            "summary": item.get("summary") or item.get("description") or page.summary,
                            "start_year": item.get("start_year") or item.get("year"),
                            "end_year": item.get("end_year"),
                            "period": item.get("period"),
                            "event_type": item.get("event_type"),
                            "importance_level": item.get("importance_level"),
                            "causes": item.get("causes"),
                            "effects": item.get("effects"),
                            "people_involved": item.get("people_involved"),
                            "locations": item.get("locations"),
                        }
                    )
                elif str(item).strip():
                    events.append({"event_name": str(item).strip(), "summary": page.summary})

        if not events:
            events.append(
                {
                    "event_name": page.title,
                    "summary": page.summary,
                    "start_year": page.start_year,
                    "end_year": page.end_year,
                    "period": page.period,
                    "event_type": page.event_type,
                    "importance_level": 3,
                }
            )

        return events

    async def _events_from_wiki_llm(self, page: WikiPage) -> list[dict[str, Any]]:
        content = page.content or {}
        wiki_content = "\n\n".join(str(v) for v in content.values() if v) if isinstance(content, dict) else ""
        prompt = (
            f"Wiki page title: {page.title}\n\n"
            f"Summary: {page.summary or ''}\n\n"
            f"Content:\n{wiki_content[:12_000]}\n\n"
            "Extract significant historical events from this wiki page and return them as a JSON array."
        )
        raw_response = await get_llm_client().generate(
            prompt,
            system=_EXTRACT_SYSTEM_PROMPT,
            max_tokens=4096,
        )
        parsed = parse_llm_json(raw_response)
        return parsed if isinstance(parsed, list) else []
