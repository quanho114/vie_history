"""Wiki Brain — wiki page CRUD routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import AdminUser, CurrentUser
from app.schemas.wiki import (
    WikiPageCreate,
    WikiPageListResponse,
    WikiPageResponse,
    WikiPageUpdate,
    WikiPageVersionResponse,
)
from app.services.wiki.wiki_service import WikiService

router = APIRouter()
wiki_service = WikiService()


@router.get("", response_model=WikiPageListResponse, summary="List wiki pages")
async def list_wiki_pages(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    period: str | None = Query(None, description="Filter by historical period"),
    event_type: str | None = Query(None, description="Filter by event type"),
    search: str | None = Query(None, description="Full-text search in title/summary"),
    project_id: str | None = Query(None, description="Filter by project workspace ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> WikiPageListResponse:
    """List wiki pages with optional filters.

    Supports filtering by status, period, event_type, project, and free-text search
    over title and summary fields.
    """
    pages, total = await wiki_service.get_pages(
        db,
        status=status_filter,
        period=period,
        event_type=event_type,
        search=search,
        project_id=project_id,
        page=page,
        page_size=page_size,
    )
    return WikiPageListResponse(
        pages=[WikiPageResponse.model_validate(p) for p in pages],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{slug}", response_model=WikiPageResponse, summary="Get wiki page by slug")
async def get_wiki_page(
    slug: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> WikiPageResponse:
    """Retrieve a single wiki page by its URL slug."""
    page = await wiki_service.get_page_by_slug(db, slug)
    if page is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wiki page with slug '{slug}' not found",
        )
    return WikiPageResponse.model_validate(page)


@router.post(
    "",
    response_model=WikiPageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create wiki page",
)
async def create_wiki_page(
    data: WikiPageCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> WikiPageResponse:
    """Manually create a new wiki page.

    The slug is auto-generated from the title if not provided.
    An initial version snapshot (v1) is created automatically.
    """
    page = await wiki_service.create_page(
        db,
        data=data.model_dump(exclude_unset=False),
        created_by_id=current_user.id,
    )
    return WikiPageResponse.model_validate(page)


@router.put("/{slug}", response_model=WikiPageResponse, summary="Update wiki page")
async def update_wiki_page(
    slug: str,
    data: WikiPageUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> WikiPageResponse:
    """Update an existing wiki page by slug.

    The page version counter is incremented and the previous content is
    archived as a ``WikiPageVersion`` snapshot.
    """
    existing = await wiki_service.get_page_by_slug(db, slug)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wiki page with slug '{slug}' not found",
        )
    updated = await wiki_service.update_page(
        db,
        wiki_page_id=existing.id,
        data=data.model_dump(exclude_unset=True),
        created_by_id=current_user.id,
    )
    return WikiPageResponse.model_validate(updated)


@router.delete(
    "/{slug}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete wiki page (admin only)",
)
async def delete_wiki_page(
    slug: str,
    current_user: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Permanently delete a wiki page and all related versions, claims, and links.

    **Admin access required.**
    """
    existing = await wiki_service.get_page_by_slug(db, slug)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wiki page with slug '{slug}' not found",
        )
    await wiki_service.delete_page(db, existing.id)


@router.get(
    "/{slug}/versions",
    response_model=list[WikiPageVersionResponse],
    summary="List wiki page versions",
)
async def list_wiki_page_versions(
    slug: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> list[WikiPageVersionResponse]:
    """List all version snapshots for a wiki page, ordered oldest to newest."""
    existing = await wiki_service.get_page_by_slug(db, slug)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wiki page with slug '{slug}' not found",
        )
    versions = await wiki_service.get_page_versions(db, existing.id)
    return [WikiPageVersionResponse.model_validate(v) for v in versions]
