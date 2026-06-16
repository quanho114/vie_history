"""DraftService — Operations for proposing, listing, and reviewing wiki page drafts."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.wiki import WikiPage, WikiPageDraft, WikiPageVersion
from app.models.project import Project
from app.services.wiki.wiki_service import _slugify_basic

logger = get_logger("draft_service")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DraftService:
    """Operations for WikiPageDraft entities."""

    async def get_draft(self, db: AsyncSession, draft_id: str) -> WikiPageDraft | None:
        """Fetch a single draft by ID."""
        result = await db.execute(select(WikiPageDraft).where(WikiPageDraft.id == draft_id))
        return result.scalar_one_or_none()

    async def get_drafts(
        self,
        db: AsyncSession,
        *,
        status: str | None = None,
        project_id: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[WikiPageDraft], int]:
        """List drafts with optional status and project filters."""
        query = select(WikiPageDraft)
        count_query = select(func.count(WikiPageDraft.id))

        if status:
            query = query.where(WikiPageDraft.status == status)
            count_query = count_query.where(WikiPageDraft.status == status)
        if project_id:
            query = query.where(WikiPageDraft.project_id == project_id)
            count_query = count_query.where(WikiPageDraft.project_id == project_id)

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        result = await db.execute(
            query.order_by(WikiPageDraft.created_at.desc()).offset(offset).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def propose_draft(
        self,
        db: AsyncSession,
        data: dict,
        proposed_by_id: str | None = None,
    ) -> WikiPageDraft:
        """Propose a wiki draft (either editing an existing page or proposing a new page)."""
        slug = data.get("slug")
        if not slug:
            slug = _slugify_basic(data["title"])

        # Check if project exists if project_id is given
        project_id = data.get("project_id")
        if project_id:
            project_res = await db.execute(select(Project).where(Project.id == project_id))
            if not project_res.scalar_one_or_none():
                raise ValueError(f"Project with ID '{project_id}' not found")

        # If wiki_page_id is given, verify it exists
        wiki_page_id = data.get("wiki_page_id")
        if wiki_page_id:
            wiki_res = await db.execute(select(WikiPage).where(WikiPage.id == wiki_page_id))
            target_page = wiki_res.scalar_one_or_none()
            if not target_page:
                raise ValueError(f"WikiPage with ID '{wiki_page_id}' not found")
            # Enforce same slug as target page for modifications
            slug = target_page.slug

        draft = WikiPageDraft(
            id=str(uuid4()),
            wiki_page_id=wiki_page_id,
            project_id=project_id,
            slug=slug,
            title=data["title"],
            summary=data.get("summary"),
            content=data.get("content"),
            status="pending",
            proposed_by=proposed_by_id,
        )
        db.add(draft)
        await db.commit()
        await db.refresh(draft)
        logger.info("wiki_page_draft_proposed", slug=draft.slug, draft_id=draft.id)
        return draft

    async def review_draft(
        self,
        db: AsyncSession,
        draft_id: str,
        reviewer_id: str,
        status: str,
        admin_notes: str | None = None,
    ) -> WikiPageDraft | None:
        """Approve or reject a proposed draft.

        If approved, merge it into the corresponding WikiPage (or create a new one).
        """
        result = await db.execute(select(WikiPageDraft).where(WikiPageDraft.id == draft_id))
        draft = result.scalar_one_or_none()
        if not draft:
            return None

        if draft.status != "pending":
            raise ValueError(f"Draft {draft_id} cannot be reviewed (current status: {draft.status})")

        if status not in ["approved", "rejected"]:
            raise ValueError("Status must be either 'approved' or 'rejected'")

        draft.status = status
        draft.reviewed_by = reviewer_id
        draft.reviewed_at = _utcnow()
        draft.admin_notes = admin_notes

        if status == "approved":
            # Merge into WikiPage
            page = None
            if draft.wiki_page_id:
                # Modifying existing page
                page_res = await db.execute(select(WikiPage).where(WikiPage.id == draft.wiki_page_id))
                page = page_res.scalar_one_or_none()

            if not page:
                # Check by slug to see if page exists
                page_res = await db.execute(select(WikiPage).where(WikiPage.slug == draft.slug))
                page = page_res.scalar_one_or_none()

            if page:
                # Save previous version snapshot
                snapshot = WikiPageVersion(
                    id=str(uuid4()),
                    wiki_page_id=page.id,
                    version=page.version,
                    content_snapshot=page.content,
                    change_summary=draft.summary or "Approved community draft",
                    created_by=draft.proposed_by,
                )
                db.add(snapshot)

                # Update the page content
                page.title = draft.title
                page.summary = draft.summary
                page.content = draft.content
                page.project_id = draft.project_id or page.project_id
                page.version = page.version + 1
                page.status = "published"
                logger.info("wiki_page_merged_from_draft", slug=page.slug, version=page.version)
            else:
                # Create a new WikiPage
                page = WikiPage(
                    id=str(uuid4()),
                    slug=draft.slug,
                    title=draft.title,
                    summary=draft.summary,
                    content=draft.content,
                    status="published",
                    version=1,
                    project_id=draft.project_id,
                    created_by=draft.proposed_by,
                )
                db.add(page)
                await db.flush()

                # Associate draft with the new page
                draft.wiki_page_id = page.id

                # Save initial version
                version = WikiPageVersion(
                    id=str(uuid4()),
                    wiki_page_id=page.id,
                    version=1,
                    content_snapshot=draft.content,
                    change_summary="Initial creation from draft",
                    created_by=draft.proposed_by,
                )
                db.add(version)
                logger.info("wiki_page_created_from_draft", slug=page.slug)

        await db.commit()
        await db.refresh(draft)
        return draft
