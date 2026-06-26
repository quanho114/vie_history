"""WikiService — CRUD operations for Wiki Brain pages, jobs, and review plans."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, func, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.wiki import (
    BrainBuildJob,
    BrainReviewPlan,
    WikiPage,
    WikiPageVersion,
)

logger = get_logger("wiki_service")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class WikiService:
    """CRUD service for Wiki Brain entities.

    All methods are async and accept an ``AsyncSession`` as the first
    argument so they integrate cleanly with FastAPI's ``Depends(get_db)``.
    """

    # ------------------------------------------------------------------
    # Wiki Pages
    # ------------------------------------------------------------------

    async def get_pages(
        self,
        db: AsyncSession,
        *,
        status: str | None = None,
        period: str | None = None,
        event_type: str | None = None,
        search: str | None = None,
        project_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[WikiPage], int]:
        """Return a paginated list of wiki pages with optional filters.

        Returns a tuple of ``(pages, total_count)``.
        """
        query = select(WikiPage)
        count_query = select(func.count(WikiPage.id))

        if status:
            query = query.where(WikiPage.status == status)
            count_query = count_query.where(WikiPage.status == status)
        if project_id:
            query = query.where(WikiPage.project_id == project_id)
            count_query = count_query.where(WikiPage.project_id == project_id)
        if period:
            if period == "khang-chien-chong-phap":
                period_filter = and_(
                    WikiPage.start_year.is_not(None),
                    WikiPage.start_year >= 1940,
                    WikiPage.start_year <= 1954
                )
            elif period == "khang-chien-chong-my":
                period_filter = and_(
                    WikiPage.start_year.is_not(None),
                    WikiPage.start_year >= 1955,
                    WikiPage.start_year <= 1975
                )
            elif period == "thong-nhat":
                period_filter = and_(
                    WikiPage.start_year.is_not(None),
                    WikiPage.start_year >= 1975
                )
            else:
                period_filter = or_(
                    WikiPage.period == period,
                    WikiPage.period.ilike(f"%{period}%")
                )
            query = query.where(period_filter)
            count_query = count_query.where(period_filter)
        if event_type:
            query = query.where(WikiPage.event_type == event_type)
            count_query = count_query.where(WikiPage.event_type == event_type)
        if search:
            like_expr = f"%{search}%"
            search_filter = or_(
                WikiPage.title.ilike(like_expr),
                WikiPage.summary.ilike(like_expr),
            )
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        result = await db.execute(
            query.order_by(WikiPage.updated_at.desc()).offset(offset).limit(page_size)
        )
        pages = list(result.scalars().all())
        return pages, total

    async def get_page_by_slug(self, db: AsyncSession, slug: str) -> WikiPage | None:
        """Return a single wiki page by its slug, or ``None`` if not found."""
        result = await db.execute(select(WikiPage).where(WikiPage.slug == slug))
        return result.scalar_one_or_none()

    async def get_page_versions(
        self, db: AsyncSession, wiki_page_id: str
    ) -> list[WikiPageVersion]:
        """Return all version snapshots for a wiki page, ordered by version ascending."""
        result = await db.execute(
            select(WikiPageVersion)
            .where(WikiPageVersion.wiki_page_id == wiki_page_id)
            .order_by(WikiPageVersion.version.asc())
        )
        return list(result.scalars().all())

    async def create_page(
        self,
        db: AsyncSession,
        data: dict,
        created_by_id: str | None = None,
    ) -> WikiPage:
        """Create a new wiki page and save an initial version snapshot.

        ``data`` should contain keys: title, slug (optional), summary, content,
        status, event_type, period, start_year, end_year, source_document_ids.
        """
        slug = data.get("slug") or _slugify_basic(data.get("title", "trang-wiki"))
        # Ensure slug uniqueness
        existing = await db.execute(select(WikiPage).where(WikiPage.slug == slug))
        if existing.scalar_one_or_none():
            slug = f"{slug}-{str(uuid4())[:8]}"

        page = WikiPage(
            id=str(uuid4()),
            slug=slug,
            title=data["title"],
            summary=data.get("summary"),
            content=data.get("content"),
            status=data.get("status", "draft"),
            version=1,
            event_type=data.get("event_type"),
            period=data.get("period"),
            start_year=data.get("start_year"),
            end_year=data.get("end_year"),
            source_document_ids=data.get("source_document_ids"),
            created_by=created_by_id,
        )
        db.add(page)
        await db.flush()

        # Save initial version snapshot
        version = WikiPageVersion(
            id=str(uuid4()),
            wiki_page_id=page.id,
            version=1,
            content_snapshot=data.get("content"),
            change_summary="Initial creation",
            created_by=created_by_id,
        )
        db.add(version)
        await db.commit()
        await db.refresh(page)
        logger.info("wiki_page_created", slug=page.slug, page_id=page.id)
        return page

    async def update_page(
        self,
        db: AsyncSession,
        wiki_page_id: str,
        data: dict,
        created_by_id: str | None = None,
    ) -> WikiPage | None:
        """Update a wiki page, incrementing the version and saving a version snapshot.

        Returns the updated page or ``None`` if not found.
        """
        result = await db.execute(select(WikiPage).where(WikiPage.id == wiki_page_id))
        page = result.scalar_one_or_none()
        if page is None:
            return None

        # Snapshot current state before mutation
        snapshot = WikiPageVersion(
            id=str(uuid4()),
            wiki_page_id=page.id,
            version=page.version,
            content_snapshot=page.content,
            change_summary=data.get("change_summary", "Manual update"),
            created_by=created_by_id,
        )
        db.add(snapshot)

        # Apply updates
        if "title" in data:
            page.title = data["title"]
        if "summary" in data:
            page.summary = data["summary"]
        if "content" in data:
            page.content = data["content"]
        if "status" in data:
            page.status = data["status"]
        if "event_type" in data:
            page.event_type = data["event_type"]
        if "period" in data:
            page.period = data["period"]
        if "start_year" in data:
            page.start_year = data["start_year"]
        if "end_year" in data:
            page.end_year = data["end_year"]
        if "source_document_ids" in data:
            page.source_document_ids = data["source_document_ids"]

        page.version = page.version + 1

        await db.commit()
        await db.refresh(page)
        logger.info("wiki_page_updated", slug=page.slug, version=page.version)
        return page

    async def delete_page(self, db: AsyncSession, wiki_page_id: str) -> bool:
        """Delete a wiki page and all related data (cascade).

        Returns ``True`` if deleted, ``False`` if not found.
        """
        result = await db.execute(select(WikiPage).where(WikiPage.id == wiki_page_id))
        page = result.scalar_one_or_none()
        if page is None:
            return False
        await db.delete(page)
        await db.commit()
        logger.info("wiki_page_deleted", page_id=wiki_page_id)
        return True

    # ------------------------------------------------------------------
    # Brain Build Jobs
    # ------------------------------------------------------------------

    async def get_build_jobs(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[BrainBuildJob], int]:
        """Return paginated build jobs ordered by creation date descending."""
        count_result = await db.execute(select(func.count(BrainBuildJob.id)))
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        result = await db.execute(
            select(BrainBuildJob)
            .order_by(BrainBuildJob.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_build_job(
        self, db: AsyncSession, job_id: str
    ) -> BrainBuildJob | None:
        """Fetch a single build job by ID."""
        result = await db.execute(
            select(BrainBuildJob).where(BrainBuildJob.id == job_id)
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------
    # Review Plans
    # ------------------------------------------------------------------

    async def get_pending_review_plans(
        self, db: AsyncSession
    ) -> list[BrainReviewPlan]:
        """Return all review plans with status ``pending``."""
        result = await db.execute(
            select(BrainReviewPlan)
            .where(BrainReviewPlan.status == "pending")
            .order_by(BrainReviewPlan.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all_review_plans(
        self,
        db: AsyncSession,
        *,
        status: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> list[BrainReviewPlan]:
        """Return all review plans (optionally filtered by status), newest first."""
        query = select(BrainReviewPlan)
        if status:
            query = query.where(BrainReviewPlan.status == status)
        offset = (page - 1) * page_size
        result = await db.execute(
            query.order_by(BrainReviewPlan.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all())

    async def get_review_plan(
        self, db: AsyncSession, plan_id: str
    ) -> BrainReviewPlan | None:
        """Fetch a single review plan by ID."""
        result = await db.execute(
            select(BrainReviewPlan).where(BrainReviewPlan.id == plan_id)
        )
        return result.scalar_one_or_none()

    async def approve_review_plan(
        self,
        db: AsyncSession,
        plan_id: str,
        admin_id: str,
        notes: str | None = None,
        execute_pipeline: bool = True,
    ) -> BrainReviewPlan | None:
        """Approve a review plan and trigger the refine/verify/commit pipeline.

        Returns the updated plan, or ``None`` if not found.
        Raises ``ValueError`` if the plan is not in ``pending`` status.
        """
        result = await db.execute(
            select(BrainReviewPlan).where(BrainReviewPlan.id == plan_id)
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            return None
        if plan.status != "pending":
            raise ValueError(
                f"Review plan {plan_id} cannot be approved (current status: {plan.status})"
            )

        plan.status = "approved"
        plan.reviewed_by = admin_id
        plan.reviewed_at = _utcnow()
        if notes:
            plan.admin_notes = notes
        await db.commit()

        if execute_pipeline:
            # Import here to avoid circular imports at module load time.
            from app.services.wiki.wiki_pipeline import WikiPipeline

            try:
                pipeline = WikiPipeline()
                await pipeline.execute_approved_plan(db, plan_id=plan_id)
            except Exception as exc:
                logger.error("approve_plan_pipeline_error", plan_id=plan_id, error=str(exc))
                # Do not re-raise; the plan is already marked approved and the job
                # status update happens inside execute_approved_plan.

        await db.refresh(plan)
        logger.info("review_plan_approved", plan_id=plan_id, admin_id=admin_id)
        return plan

    async def reject_review_plan(
        self,
        db: AsyncSession,
        plan_id: str,
        admin_id: str,
        notes: str | None = None,
    ) -> BrainReviewPlan | None:
        """Reject a review plan.

        Returns the updated plan, or ``None`` if not found.
        Raises ``ValueError`` if the plan is not in ``pending`` status.
        """
        result = await db.execute(
            select(BrainReviewPlan).where(BrainReviewPlan.id == plan_id)
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            return None
        if plan.status != "pending":
            raise ValueError(
                f"Review plan {plan_id} cannot be rejected (current status: {plan.status})"
            )

        plan.status = "rejected"
        plan.reviewed_by = admin_id
        plan.reviewed_at = _utcnow()
        if notes:
            plan.admin_notes = notes

        # Mark the parent job as done (no pages will be created)
        job_result = await db.execute(
            select(BrainBuildJob).where(BrainBuildJob.id == plan.job_id)
        )
        job = job_result.scalar_one_or_none()
        if job:
            job.status = "done"
            job.finished_at = _utcnow()
            job.result_summary = {
                **(job.result_summary or {}),
                "rejected": True,
                "admin_notes": notes,
            }

        await db.commit()
        await db.refresh(plan)
        logger.info("review_plan_rejected", plan_id=plan_id, admin_id=admin_id)
        return plan


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _slugify_basic(text: str) -> str:
    """Simple ASCII slug — mirrors the pipeline's _slugify without a regex import."""
    import re

    text = text.lower().strip()
    replacements = {
        "à": "a", "á": "a", "ạ": "a", "ả": "a", "ã": "a",
        "â": "a", "ầ": "a", "ấ": "a", "ậ": "a", "ẩ": "a", "ẫ": "a",
        "ă": "a", "ằ": "a", "ắ": "a", "ặ": "a", "ẳ": "a", "ẵ": "a",
        "è": "e", "é": "e", "ẹ": "e", "ẻ": "e", "ẽ": "e",
        "ê": "e", "ề": "e", "ế": "e", "ệ": "e", "ể": "e", "ễ": "e",
        "ì": "i", "í": "i", "ị": "i", "ỉ": "i", "ĩ": "i",
        "ò": "o", "ó": "o", "ọ": "o", "ỏ": "o", "õ": "o",
        "ô": "o", "ồ": "o", "ố": "o", "ộ": "o", "ổ": "o", "ỗ": "o",
        "ơ": "o", "ờ": "o", "ớ": "o", "ợ": "o", "ở": "o", "ỡ": "o",
        "ù": "u", "ú": "u", "ụ": "u", "ủ": "u", "ũ": "u",
        "ư": "u", "ừ": "u", "ứ": "u", "ự": "u", "ử": "u", "ữ": "u",
        "ỳ": "y", "ý": "y", "ỵ": "y", "ỷ": "y", "ỹ": "y",
        "đ": "d",
    }
    for viet, ascii_ch in replacements.items():
        text = text.replace(viet, ascii_ch)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text)
    return re.sub(r"-+", "-", text).strip("-")[:450]
