"""Brain Builder — job management and review plan approval routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, get_db_context
from app.core.config import settings
from app.core.security import CurrentUser
from app.schemas.wiki import (
    ApproveReviewPlanRequest,
    BrainBuildJobListResponse,
    BrainBuildJobResponse,
    BrainReviewPlanListResponse,
    BrainReviewPlanResponse,
    StartBuildJobRequest,
)
from app.services.wiki.wiki_pipeline import WikiPipeline
from app.services.wiki.wiki_service import WikiService

router = APIRouter()
wiki_service = WikiService()
wiki_pipeline = WikiPipeline()


async def _execute_approved_plan_background(plan_id: str) -> None:
    async with get_db_context() as db:
        await wiki_pipeline.execute_approved_plan(db, plan_id=plan_id)


# ---------------------------------------------------------------------------
# Brain Build Jobs
# ---------------------------------------------------------------------------

@router.post(
    "/jobs",
    response_model=BrainBuildJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start a wiki brain build job",
)
async def start_build_job(
    data: StartBuildJobRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> BrainBuildJobResponse:
    """Start a new wiki brain build pipeline over the specified documents.

    The pipeline will:
    1. Map — extract key points from each document.
    2. Reduce — group into historical topics.
    3. Plan — propose wiki pages for admin review.

    The returned job will be in ``awaiting_review`` status once planning completes.
    The refine/verify/commit steps are triggered only after an admin approves the
    associated review plan.
    """
    job = await wiki_pipeline.run(
        db,
        document_ids=data.document_ids,
        created_by_id=current_user.id,
    )
    return BrainBuildJobResponse.model_validate(job)


@router.get(
    "/jobs",
    response_model=BrainBuildJobListResponse,
    summary="List brain build jobs",
)
async def list_build_jobs(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> BrainBuildJobListResponse:
    """Return a paginated list of all brain build jobs."""
    jobs, total = await wiki_service.get_build_jobs(db, page=page, page_size=page_size)
    return BrainBuildJobListResponse(
        jobs=[BrainBuildJobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/jobs/{job_id}",
    response_model=BrainBuildJobResponse,
    summary="Get build job status",
)
async def get_build_job(
    job_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> BrainBuildJobResponse:
    """Get the current status and logs of a specific brain build job."""
    job = await wiki_service.get_build_job(db, job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Build job '{job_id}' not found",
        )
    return BrainBuildJobResponse.model_validate(job)


# ---------------------------------------------------------------------------
# Review Plans
# ---------------------------------------------------------------------------

@router.get(
    "/plans",
    response_model=BrainReviewPlanListResponse,
    summary="List review plans",
)
async def list_review_plans(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None, description="Filter by status: pending | approved | rejected | partial"),
) -> BrainReviewPlanListResponse:
    """Return review plans. Defaults to all statuses; pass ?status=pending to filter."""
    plans = await wiki_service.get_all_review_plans(db, status=status)
    return BrainReviewPlanListResponse(
        plans=[BrainReviewPlanResponse.model_validate(p) for p in plans],
        total=len(plans),
    )


@router.get(
    "/plans/{plan_id}",
    response_model=BrainReviewPlanResponse,
    summary="Get review plan detail",
)
async def get_review_plan(
    plan_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> BrainReviewPlanResponse:
    """Get full detail of a single review plan, including all proposed pages."""
    plan = await wiki_service.get_review_plan(db, plan_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review plan '{plan_id}' not found",
        )
    return BrainReviewPlanResponse.model_validate(plan)


@router.post(
    "/plans/{plan_id}/approve",
    response_model=BrainReviewPlanResponse,
    summary="Approve review plan (admin only)",
)
async def approve_review_plan(
    plan_id: str,
    data: ApproveReviewPlanRequest,
    background_tasks: BackgroundTasks,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> BrainReviewPlanResponse:
    """Approve a review plan and trigger the refine→verify→commit pipeline.

    Once approved, the pipeline will write full wiki page content for each
    proposed page and persist them to the database.

    **Admin access required.**
    """
    if current_user.role != "admin" and settings.APP_ENV != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        plan = await wiki_service.approve_review_plan(
            db,
            plan_id=plan_id,
            admin_id=current_user.id,
            notes=data.notes,
            execute_pipeline=False,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review plan '{plan_id}' not found",
        )
    background_tasks.add_task(_execute_approved_plan_background, plan_id)
    return BrainReviewPlanResponse.model_validate(plan)


@router.post(
    "/plans/{plan_id}/reject",
    response_model=BrainReviewPlanResponse,
    summary="Reject review plan (admin only)",
)
async def reject_review_plan(
    plan_id: str,
    data: ApproveReviewPlanRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> BrainReviewPlanResponse:
    """Reject a review plan.

    The associated build job is marked as ``done`` without creating any wiki pages.

    **Admin access required.**
    """
    if current_user.role != "admin" and settings.APP_ENV != "development":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )

    try:
        plan = await wiki_service.reject_review_plan(
            db,
            plan_id=plan_id,
            admin_id=current_user.id,
            notes=data.notes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review plan '{plan_id}' not found",
        )
    return BrainReviewPlanResponse.model_validate(plan)
