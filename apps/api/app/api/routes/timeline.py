"""Timeline Brain API routes.

Prefix (set by main.py): /api/v1/timeline
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.schemas.timeline import (
    ExtractEventsRequest,
    HistoricalEventCreate,
    HistoricalEventListResponse,
    HistoricalEventResponse,
    HistoricalEventUpdate,
)
from app.services.timeline.timeline_service import TimelineService

router = APIRouter()
_svc = TimelineService()


# ---------------------------------------------------------------------------
# List events
# ---------------------------------------------------------------------------


@router.get("/events", response_model=HistoricalEventListResponse)
async def list_events(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    period: str | None = Query(default=None, description="Filter by historical period"),
    start_year: int | None = Query(default=None, description="Events starting at or after this year"),
    end_year: int | None = Query(default=None, description="Events up to this year"),
    event_type: str | None = Query(default=None, description="battle | treaty | political | cultural | economic"),
    search: str | None = Query(default=None, description="Full-text search on name/summary"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
):
    """Return a paginated, optionally filtered list of historical events."""
    events, total = await _svc.get_events(
        db,
        period=period,
        start_year=start_year,
        end_year=end_year,
        event_type=event_type,
        search=search,
        page=page,
        page_size=page_size,
    )
    return HistoricalEventListResponse(
        events=[HistoricalEventResponse.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# Extract events from document  (must come BEFORE /{slug} to avoid routing collision)
# ---------------------------------------------------------------------------


@router.post("/events/extract", status_code=status.HTTP_201_CREATED)
async def extract_events(
    body: ExtractEventsRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Auto-extract historical events from an ingested document via LLM."""
    try:
        events = await _svc.extract_events_from_document(
            db, document_id=body.document_id
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    await db.commit()

    return {
        "extracted_count": len(events),
        "events": [HistoricalEventResponse.model_validate(e) for e in events],
    }


# ---------------------------------------------------------------------------
# Get single event by slug
# ---------------------------------------------------------------------------


@router.get("/events/{slug}", response_model=HistoricalEventResponse)
async def get_event(
    slug: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve a single historical event by its URL slug."""
    event = await _svc.get_event_by_slug(db, slug)
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event not found: {slug}",
        )
    return HistoricalEventResponse.model_validate(event)


# ---------------------------------------------------------------------------
# Create event
# ---------------------------------------------------------------------------


@router.post("/events", response_model=HistoricalEventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(
    body: HistoricalEventCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Manually create a new historical event."""
    try:
        event = await _svc.create_event(db, body.model_dump(exclude_none=True))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    await db.commit()
    await db.refresh(event)
    return HistoricalEventResponse.model_validate(event)


# ---------------------------------------------------------------------------
# Update event
# ---------------------------------------------------------------------------


@router.put("/events/{slug}", response_model=HistoricalEventResponse)
async def update_event(
    slug: str,
    body: HistoricalEventUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Update an existing historical event by slug."""
    existing = await _svc.get_event_by_slug(db, slug)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event not found: {slug}",
        )

    try:
        event = await _svc.update_event(
            db, existing.id, body.model_dump(exclude_none=True)
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    await db.commit()
    await db.refresh(event)
    return HistoricalEventResponse.model_validate(event)


# ---------------------------------------------------------------------------
# Delete event
# ---------------------------------------------------------------------------


@router.delete("/events/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    slug: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Delete a historical event by slug."""
    existing = await _svc.get_event_by_slug(db, slug)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event not found: {slug}",
        )

    await _svc.delete_event(db, existing.id)
    await db.commit()
