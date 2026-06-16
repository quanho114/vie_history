"""Wiki Brain Pipeline — orchestrates a Map→Reduce→Plan→(Review)→Refine→Verify→Commit flow.

Pipeline phases
---------------
1. **Map**   – LLM reads each document and extracts key points (events, people, claims).
2. **Reduce** – LLM groups mapped results into coherent topics / historical events.
3. **Plan**  – LLM proposes a list of wiki pages to create/update; persisted as
                a ``BrainReviewPlan`` with status ``pending``.
4. *(pause)* – Admin reviews & approves the plan via the REST API.
5. **Refine** – LLM writes full structured content for each approved page.
6. **Verify** – LLM checks that every claim in the draft is supported by a source chunk.
7. **Commit** – Saves ``WikiPage`` + ``WikiPageVersion`` + ``WikiClaim`` + ``WikiSource`` rows.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.document import Document, DocumentChunk
from app.models.wiki import (
    BrainBuildJob,
    BrainReviewPlan,
    WikiClaim,
    WikiPage,
    WikiPageVersion,
    WikiSource,
)
from app.services.llm.client import get_llm_client
from app.services.llm.json_parser import parse_llm_json
from app.services.wiki.prompts import (
    MAP_SYSTEM_PROMPT,
    MAP_USER_TEMPLATE,
    PLAN_SYSTEM_PROMPT,
    PLAN_USER_TEMPLATE,
    REDUCE_SYSTEM_PROMPT,
    REDUCE_USER_TEMPLATE,
    REFINE_SYSTEM_PROMPT,
    REFINE_USER_TEMPLATE,
    VERIFY_SYSTEM_PROMPT,
    VERIFY_USER_TEMPLATE,
)

logger = get_logger("wiki_pipeline")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slugify(text: str) -> str:
    """Convert a Vietnamese title to an ASCII URL slug."""
    # Basic transliteration – in production consider using python-slugify with vi support
    text = text.lower().strip()
    text = re.sub(r"[àáạảãâầấậẩẫăằắặẳẵ]", "a", text)
    text = re.sub(r"[èéẹẻẽêềếệểễ]", "e", text)
    text = re.sub(r"[ìíịỉĩ]", "i", text)
    text = re.sub(r"[òóọỏõôồốộổỗơờớợởỡ]", "o", text)
    text = re.sub(r"[ùúụủũưừứựửữ]", "u", text)
    text = re.sub(r"[ỳýỵỷỹ]", "y", text)
    text = re.sub(r"[đ]", "d", text)
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"[\s]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text[:450]  # stay within String(500) with room for suffix


# Alias so existing call-sites in this module remain unchanged
_parse_llm_json = parse_llm_json


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Pipeline class
# ---------------------------------------------------------------------------

class WikiPipeline:
    """Orchestrates the full wiki-brain pipeline.

    Usage::

        pipeline = WikiPipeline()
        job = await pipeline.run(db, document_ids=["id1", "id2"], created_by_id="user-uuid")
        # job.status == "awaiting_review" → admin approves via WikiService
        await pipeline.execute_approved_plan(db, plan_id=job.review_plan.id)
    """

    # ------------------------------------------------------------------
    # Public entry points
    # ------------------------------------------------------------------

    async def run(
        self,
        db: AsyncSession,
        document_ids: list[str],
        created_by_id: str | None = None,
    ) -> BrainBuildJob:
        """Start the pipeline: MAP → REDUCE → PLAN, then pause for admin review.

        Returns the ``BrainBuildJob`` in ``awaiting_review`` status after the
        plan has been persisted.  The refine/verify/commit steps are deferred
        until an admin approves the plan via ``execute_approved_plan()``.
        """
        job = BrainBuildJob(
            id=str(uuid4()),
            job_type="wiki_build",
            status="running",
            source_document_ids=document_ids,
            created_by=created_by_id,
            started_at=_utcnow(),
            logs=[],
        )
        db.add(job)
        await db.flush()

        try:
            self._log(job, "Pipeline started", {"document_ids": document_ids})

            # Load documents
            documents = await self._load_documents(db, document_ids)
            if not documents:
                raise ValueError("No valid documents found for the given IDs")

            self._log(job, "Documents loaded", {"count": len(documents)})

            # Map
            mapped_results = await self._map_step(db, documents)
            self._log(job, "Map step completed", {"mapped_count": len(mapped_results)})

            # Reduce
            reduced = await self._reduce_step(mapped_results)
            self._log(job, "Reduce step completed", {"topic_count": len(reduced.get("topics", []))})

            # Plan
            plan = await self._plan_step(db, reduced, job, created_by_id)
            self._log(job, "Plan step completed", {"plan_id": plan.id})

            # Pause for admin review
            job.status = "awaiting_review"
            job.result_summary = {
                "plan_id": plan.id,
                "proposed_pages_count": len(plan.proposed_pages),
                "document_count": len(documents),
            }
            await db.commit()
            logger.info("wiki_pipeline_awaiting_review", job_id=job.id, plan_id=plan.id)
            return job

        except Exception as exc:
            logger.error("wiki_pipeline_error", job_id=job.id, error=str(exc))
            job.status = "failed"
            job.error_message = str(exc)
            job.finished_at = _utcnow()
            await db.commit()
            raise

    async def execute_approved_plan(
        self,
        db: AsyncSession,
        plan_id: str,
    ) -> list[WikiPage]:
        """Execute the REFINE → VERIFY → COMMIT steps for an approved review plan.

        Called automatically by ``WikiService.approve_review_plan()``.
        Returns the list of committed ``WikiPage`` instances.
        """
        result = await db.execute(
            select(BrainReviewPlan).where(BrainReviewPlan.id == plan_id)
        )
        plan = result.scalar_one_or_none()
        if plan is None:
            raise ValueError(f"Review plan {plan_id} not found")
        if plan.status != "approved":
            raise ValueError(f"Review plan {plan_id} is not approved (status={plan.status})")

        job_result = await db.execute(
            select(BrainBuildJob).where(BrainBuildJob.id == plan.job_id)
        )
        job = job_result.scalar_one_or_none()
        if job is None:
            raise ValueError(f"BrainBuildJob for plan {plan_id} not found")

        job.status = "running"
        await db.flush()

        created_pages: list[WikiPage] = []
        timeline_events_created = 0
        graph_nodes_created = 0
        graph_edges_created = 0
        linking_errors: list[dict[str, str]] = []
        try:
            for page_draft in plan.proposed_pages:
                # Load source documents for context
                source_doc_ids = page_draft.get("source_document_ids", [])
                source_docs = await self._load_documents(db, source_doc_ids)
                source_chunks = await self._load_chunks(db, source_doc_ids)

                # Refine
                refined_content = await self._refine_step(db, page_draft, source_docs)
                logger.info("refine_step_done", slug=page_draft.get("slug"))

                # Verify
                verified = await self._verify_step(db, page_draft, refined_content, source_chunks)
                logger.info("verify_step_done", slug=page_draft.get("slug"))

                # Commit
                wiki_page = await self._commit_step(
                    db,
                    page_draft=page_draft,
                    verified=verified,
                    refined_content=refined_content,
                    job_id=job.id,
                    created_by_id=job.created_by,
                )
                created_pages.append(wiki_page)
                logger.info("commit_step_done", slug=wiki_page.slug, page_id=wiki_page.id)

                try:
                    linked = await self._link_second_brain_stores(db, wiki_page)
                    timeline_events_created += linked["timeline_events"]
                    graph_nodes_created += linked["graph_nodes"]
                    graph_edges_created += linked["graph_edges"]
                    self._log(job, "Second brain linking completed", {"page_id": wiki_page.id, **linked})
                except Exception as link_exc:
                    logger.error(
                        "second_brain_linking_error",
                        page_id=wiki_page.id,
                        slug=wiki_page.slug,
                        error=str(link_exc),
                    )
                    error_entry = {"page_id": wiki_page.id, "slug": wiki_page.slug, "error": str(link_exc)}
                    linking_errors.append(error_entry)
                    self._log(job, "Second brain linking failed", error_entry)

            job.status = "partial" if linking_errors else "done"
            job.finished_at = _utcnow()
            job.result_summary = {
                **(job.result_summary or {}),
                "committed_pages": [p.id for p in created_pages],
                "wiki_pages_created": len(created_pages),
                "timeline_events_created": timeline_events_created,
                "graph_nodes_created": graph_nodes_created,
                "graph_edges_created": graph_edges_created,
                "linking_errors": linking_errors,
            }
            if linking_errors:
                job.error_message = "Wiki pages were committed, but some Timeline/Graph linking steps failed."
            await db.commit()
            return created_pages

        except Exception as exc:
            logger.error("execute_approved_plan_error", plan_id=plan_id, error=str(exc))
            job.status = "failed"
            job.error_message = str(exc)
            job.finished_at = _utcnow()
            await db.commit()
            raise

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------

    async def _map_step(
        self,
        db: AsyncSession,
        documents: list[Document],
    ) -> list[dict]:
        """Call LLM on each document to extract key historical points.

        Returns a list of dicts, one per document, with events / claims / summary.
        """
        llm = get_llm_client()
        results: list[dict] = []

        for doc in documents:
            # Load content from markdown path or fall back to summary
            content = await self._get_doc_content(doc)
            if not content:
                logger.warning("map_step_empty_content", doc_id=doc.id)
                continue

            prompt = MAP_USER_TEMPLATE.format(
                title=doc.title,
                content=content[:8000],  # guard against huge docs
                document_id=doc.id,
            )
            try:
                raw = await llm.generate(
                    prompt,
                    system=MAP_SYSTEM_PROMPT,
                    max_tokens=2000,
                )
                parsed = _parse_llm_json(raw)
                parsed["document_id"] = doc.id  # ensure ID is always set
                results.append(parsed)
            except Exception as exc:
                logger.error("map_step_error", doc_id=doc.id, error=str(exc))
                # Skip this document rather than aborting the whole pipeline
                results.append({
                    "document_id": doc.id,
                    "title": doc.title,
                    "error": str(exc),
                    "key_events": [],
                    "main_claims": [],
                    "summary": "",
                })

        return results

    async def _reduce_step(self, mapped_results: list[dict]) -> dict:
        """Group mapped results into coherent historical topics.

        Returns a dict with a ``topics`` list.
        """
        llm = get_llm_client()
        prompt = REDUCE_USER_TEMPLATE.format(
            doc_count=len(mapped_results),
            mapped_results=json.dumps(mapped_results, ensure_ascii=False, indent=2)[:12000],
        )
        try:
            raw = await llm.generate(prompt, system=REDUCE_SYSTEM_PROMPT, max_tokens=2000)
            return _parse_llm_json(raw)
        except Exception as exc:
            logger.error("reduce_step_error", error=str(exc))
            # Return a minimal structure so the pipeline can continue
            doc_ids = [r.get("document_id", "") for r in mapped_results]
            return {
                "topics": [
                    {
                        "topic_key": "general-history",
                        "title": "Lịch sử Việt Nam",
                        "period": "1945-1975",
                        "event_type": "general",
                        "summary": "Tổng hợp lịch sử từ các tài liệu đã phân tích.",
                        "source_document_ids": doc_ids,
                        "key_events": [],
                        "main_claims": [],
                    }
                ]
            }

    async def _plan_step(
        self,
        db: AsyncSession,
        reduced: dict,
        job: BrainBuildJob,
        created_by_id: str | None,
    ) -> BrainReviewPlan:
        """Propose wiki pages and persist a ``BrainReviewPlan`` for admin review."""
        llm = get_llm_client()

        # Fetch existing slugs to avoid duplicates
        existing_slugs_result = await db.execute(select(WikiPage.slug))
        existing_slugs = [row[0] for row in existing_slugs_result.all()]

        prompt = PLAN_USER_TEMPLATE.format(
            topics_json=json.dumps(reduced.get("topics", []), ensure_ascii=False, indent=2)[:10000],
            existing_slugs=json.dumps(existing_slugs, ensure_ascii=False),
        )
        try:
            raw = await llm.generate(prompt, system=PLAN_SYSTEM_PROMPT, max_tokens=2000)
            plan_data = _parse_llm_json(raw)
            proposed_pages = plan_data.get("proposed_pages", [])
        except Exception as exc:
            logger.error("plan_step_llm_error", error=str(exc))
            # Build a minimal plan from the reduce output so pipeline doesn't die
            proposed_pages = []
            for topic in reduced.get("topics", []):
                slug = _slugify(topic.get("title", "trang-wiki"))
                if slug in existing_slugs:
                    slug = f"{slug}-{str(uuid4())[:8]}"
                proposed_pages.append({
                    "action": "create",
                    "slug": slug,
                    "title": topic.get("title", "Trang Wiki"),
                    "summary": topic.get("summary", ""),
                    "period": topic.get("period"),
                    "event_type": topic.get("event_type"),
                    "source_document_ids": topic.get("source_document_ids", []),
                    "content_outline": {},
                    "topic_key": topic.get("topic_key", ""),
                })

        # Ensure unique slugs
        seen_slugs: set[str] = set(existing_slugs)
        for page in proposed_pages:
            base_slug = _slugify(page.get("slug") or page.get("title", "trang-wiki"))
            slug = base_slug
            if slug in seen_slugs:
                slug = f"{base_slug}-{str(uuid4())[:8]}"
            page["slug"] = slug
            seen_slugs.add(slug)

        plan = BrainReviewPlan(
            id=str(uuid4()),
            job_id=job.id,
            proposed_pages=proposed_pages,
            status="pending",
        )
        db.add(plan)
        await db.flush()
        return plan

    async def _refine_step(
        self,
        db: AsyncSession,
        page_draft: dict,
        source_docs: list[Document],
    ) -> dict:
        """Write full structured wiki page content using LLM.

        Returns a dict matching the ``WikiPage.content`` schema.
        """
        llm = get_llm_client()

        # Build source context (truncated to stay within token limits)
        source_summaries = []
        for doc in source_docs[:5]:  # limit to 5 docs to keep prompt manageable
            content_snippet = await self._get_doc_content(doc)
            source_summaries.append(
                f"--- {doc.title} ---\n{content_snippet[:2000] if content_snippet else '(no content)'}"
            )

        prompt = REFINE_USER_TEMPLATE.format(
            title=page_draft.get("title", ""),
            content_outline=json.dumps(
                page_draft.get("content_outline", {}), ensure_ascii=False
            ),
            source_docs="\n\n".join(source_summaries)[:8000],
        )
        try:
            raw = await llm.generate(prompt, system=REFINE_SYSTEM_PROMPT, max_tokens=2000)
            return _parse_llm_json(raw)
        except Exception as exc:
            logger.error("refine_step_error", slug=page_draft.get("slug"), error=str(exc))
            return {
                "background": page_draft.get("summary", ""),
                "causes": "",
                "main_events": "",
                "results": "",
                "significance": "",
                "people": [],
                "timeline": [],
                "references": [],
            }

    async def _verify_step(
        self,
        db: AsyncSession,
        page_draft: dict,
        refined_content: dict,
        chunks: list[DocumentChunk],
    ) -> dict:
        """Verify that claims in the refined content have source support.

        Returns a dict with ``verified_claims`` and ``overall_confidence``.
        """
        llm = get_llm_client()

        chunks_text = "\n\n".join(
            f"[chunk_id={c.id}, doc_id={c.document_id}]\n{c.content[:500]}"
            for c in chunks[:20]  # limit chunks to avoid overflowing context
        )

        prompt = VERIFY_USER_TEMPLATE.format(
            title=page_draft.get("title", ""),
            page_content=json.dumps(refined_content, ensure_ascii=False)[:5000],
            chunks=chunks_text[:8000],
        )
        try:
            raw = await llm.generate(prompt, system=VERIFY_SYSTEM_PROMPT, max_tokens=2000)
            return _parse_llm_json(raw)
        except Exception as exc:
            logger.error("verify_step_error", slug=page_draft.get("slug"), error=str(exc))
            return {"verified_claims": [], "overall_confidence": 0.0}

    async def _commit_step(
        self,
        db: AsyncSession,
        page_draft: dict,
        verified: dict,
        refined_content: dict,
        job_id: str,
        created_by_id: str | None,
    ) -> WikiPage:
        """Persist the final WikiPage, WikiPageVersion, WikiClaims, and WikiSources."""
        slug = page_draft.get("slug", _slugify(page_draft.get("title", "trang-wiki")))

        # Check for existing page (update flow)
        existing_result = await db.execute(select(WikiPage).where(WikiPage.slug == slug))
        existing = existing_result.scalar_one_or_none()

        if existing:
            # Save current version as a snapshot before updating
            version_snapshot = WikiPageVersion(
                id=str(uuid4()),
                wiki_page_id=existing.id,
                version=existing.version,
                content_snapshot=existing.content,
                change_summary=f"Auto-updated by BrainBuildJob {job_id}",
                created_by=created_by_id,
            )
            db.add(version_snapshot)

            existing.title = page_draft.get("title", existing.title)
            existing.summary = page_draft.get("summary", existing.summary)
            existing.content = refined_content
            existing.status = "draft"
            existing.version = existing.version + 1
            existing.event_type = page_draft.get("event_type", existing.event_type)
            existing.period = page_draft.get("period", existing.period)
            existing.start_year = page_draft.get("start_year", existing.start_year)
            existing.end_year = page_draft.get("end_year", existing.end_year)
            existing.source_document_ids = page_draft.get(
                "source_document_ids", existing.source_document_ids
            )
            wiki_page = existing
        else:
            wiki_page = WikiPage(
                id=str(uuid4()),
                slug=slug,
                title=page_draft.get("title", "Untitled"),
                summary=page_draft.get("summary"),
                content=refined_content,
                status="draft",
                version=1,
                event_type=page_draft.get("event_type"),
                period=page_draft.get("period"),
                start_year=page_draft.get("start_year"),
                end_year=page_draft.get("end_year"),
                source_document_ids=page_draft.get("source_document_ids"),
                created_by=created_by_id,
            )
            db.add(wiki_page)
            await db.flush()

            # Initial version snapshot
            initial_version = WikiPageVersion(
                id=str(uuid4()),
                wiki_page_id=wiki_page.id,
                version=1,
                content_snapshot=refined_content,
                change_summary=f"Initial draft from BrainBuildJob {job_id}",
                created_by=created_by_id,
            )
            db.add(initial_version)

        await db.flush()

        # Persist verified claims and their sources
        for claim_data in verified.get("verified_claims", []):
            claim = WikiClaim(
                id=str(uuid4()),
                wiki_page_id=wiki_page.id,
                claim_text=claim_data.get("claim_text", ""),
                section=claim_data.get("section"),
                confidence=float(claim_data.get("confidence", 0.0)),
                verified=bool(claim_data.get("verified", False)),
            )
            db.add(claim)
            await db.flush()

            for source_data in claim_data.get("sources", []):
                source = WikiSource(
                    id=str(uuid4()),
                    wiki_claim_id=claim.id,
                    document_id=source_data.get("document_id") or None,
                    chunk_id=source_data.get("chunk_id") or None,
                    excerpt=source_data.get("excerpt"),
                    relevance_score=float(source_data.get("relevance_score", 0.0)),
                )
                db.add(source)

        await db.flush()
        return wiki_page

    async def _link_second_brain_stores(
        self,
        db: AsyncSession,
        wiki_page: WikiPage,
    ) -> dict[str, int]:
        """Populate Timeline and Graph stores from a committed wiki page."""
        from app.services.graph.graph_service import GraphService
        from app.services.timeline.timeline_service import TimelineService

        timeline_events = await TimelineService().extract_events_from_wiki_page(
            db,
            wiki_page_id=wiki_page.id,
        )
        nodes, edges = await GraphService().extract_graph_from_wiki_page(
            db,
            wiki_page_id=wiki_page.id,
        )
        return {
            "timeline_events": len(timeline_events),
            "graph_nodes": len(nodes),
            "graph_edges": len(edges),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _load_documents(
        self, db: AsyncSession, document_ids: list[str]
    ) -> list[Document]:
        """Fetch Document rows for the given IDs."""
        if not document_ids:
            return []
        result = await db.execute(
            select(Document).where(Document.id.in_(document_ids))
        )
        return list(result.scalars().all())

    async def _load_chunks(
        self, db: AsyncSession, document_ids: list[str]
    ) -> list[DocumentChunk]:
        """Fetch document chunks for a list of document IDs (used in verify step)."""
        if not document_ids:
            return []
        result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id.in_(document_ids))
            .limit(50)
        )
        return list(result.scalars().all())

    async def _get_doc_content(self, doc: Document) -> str:
        """Return the best available text content for a document."""
        if doc.markdown_content_path:
            try:
                import aiofiles
                async with aiofiles.open(doc.markdown_content_path, "r", encoding="utf-8") as f:
                    return await f.read()
            except Exception:
                pass
        return doc.summary or doc.title

    @staticmethod
    def _log(job: BrainBuildJob, message: str, data: dict | None = None) -> None:
        """Append a log entry to the job's in-memory log list."""
        entry: dict[str, Any] = {
            "ts": _utcnow().isoformat(),
            "message": message,
        }
        if data:
            entry["data"] = data
        if job.logs is None:
            job.logs = []
        job.logs = [*job.logs, entry]  # create new list to trigger JSONB change detection
