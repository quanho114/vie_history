"""API routes for Wiki Page Drafts."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.schemas.project import (
    WikiPageDraftCreate,
    WikiPageDraftResponse,
    WikiPageDraftReview,
)
from app.services.wiki.draft_service import DraftService

router = APIRouter()
draft_service = DraftService()


@router.post(
    "",
    response_model=WikiPageDraftResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Propose wiki page draft",
)
async def propose_draft(
    data: WikiPageDraftCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> WikiPageDraftResponse:
    """Propose a new wiki page or edits to an existing wiki page.

    The draft is created in a 'pending' state awaiting editor or admin review.
    """
    try:
        draft = await draft_service.propose_draft(
            db,
            data=data.model_dump(exclude_unset=True),
            proposed_by_id=current_user.id,
        )
        return WikiPageDraftResponse.model_validate(draft)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("", response_model=list[WikiPageDraftResponse], summary="List wiki drafts")
async def list_drafts(
    current_user: CurrentUser,
    status_filter: str | None = Query(None, alias="status", description="Filter by status (pending, approved, rejected)"),
    project_id: str | None = Query(None, description="Filter by project workspace ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> list[WikiPageDraftResponse]:
    """Retrieve drafts with optional filters (e.g. pending drafts)."""
    drafts, _ = await draft_service.get_drafts(
        db,
        status=status_filter,
        project_id=project_id,
        page=page,
        page_size=page_size,
    )
    return [WikiPageDraftResponse.model_validate(d) for d in drafts]


@router.get("/{id}", response_model=WikiPageDraftResponse, summary="Get draft by ID")
async def get_draft(
    id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> WikiPageDraftResponse:
    """Fetch details of a single proposed draft."""
    draft = await draft_service.get_draft(db, id)
    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Draft with ID '{id}' not found",
        )
    return WikiPageDraftResponse.model_validate(draft)


@router.post("/{id}/review", response_model=WikiPageDraftResponse, summary="Review draft")
async def review_draft(
    id: str,
    data: WikiPageDraftReview,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> WikiPageDraftResponse:
    """Approve or reject a proposed draft.

    Only admins or editors are allowed to review drafts.
    If approved, the changes are merged into the target WikiPage.
    """
    if current_user.role not in ["admin", "editor"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and editors can review drafts",
        )

    try:
        draft = await draft_service.review_draft(
            db,
            draft_id=id,
            reviewer_id=current_user.id,
            status=data.status,
            admin_notes=data.admin_notes,
        )
        if not draft:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Draft with ID '{id}' not found",
            )
        return WikiPageDraftResponse.model_validate(draft)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
