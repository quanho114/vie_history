"""Pydantic schemas for the Timeline Brain (historical events)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class HistoricalEventCreate(BaseModel):
    """Payload for manually creating a historical event."""

    event_name: str = Field(..., min_length=1, max_length=500)
    slug: str | None = Field(default=None, max_length=500)
    summary: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    start_year: int | None = None
    end_year: int | None = None
    period: str | None = None
    importance_level: int = Field(default=1, ge=1, le=5)
    event_type: str | None = None
    causes: list[str] | None = None
    effects: list[str] | None = None
    people_involved: list[str] | None = None
    locations: list[str] | None = None
    wiki_page_id: str | None = None
    source_document_ids: list[str] | None = None
    metadata_json: dict[str, Any] | None = None


class HistoricalEventUpdate(BaseModel):
    """Payload for partially updating a historical event (all fields optional)."""

    event_name: str | None = Field(default=None, max_length=500)
    slug: str | None = Field(default=None, max_length=500)
    summary: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    start_year: int | None = None
    end_year: int | None = None
    period: str | None = None
    importance_level: int | None = Field(default=None, ge=1, le=5)
    event_type: str | None = None
    causes: list[str] | None = None
    effects: list[str] | None = None
    people_involved: list[str] | None = None
    locations: list[str] | None = None
    wiki_page_id: str | None = None
    source_document_ids: list[str] | None = None
    metadata_json: dict[str, Any] | None = None


class ExtractEventsRequest(BaseModel):
    """Request to auto-extract events from an existing document."""

    document_id: str


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class HistoricalEventResponse(BaseModel):
    """Full historical event response."""

    id: str
    event_name: str
    slug: str | None
    summary: str | None
    start_date: datetime | None
    end_date: datetime | None
    start_year: int | None
    end_year: int | None
    period: str | None
    importance_level: int
    event_type: str | None
    causes: list[str] | None
    effects: list[str] | None
    people_involved: list[str] | None
    locations: list[str] | None
    wiki_page_id: str | None
    wiki_page_slug: str | None = None
    source_document_ids: list[str] | None
    metadata_json: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class HistoricalEventListResponse(BaseModel):
    """Paginated list of historical events."""

    events: list[HistoricalEventResponse]
    total: int
    page: int
    page_size: int
