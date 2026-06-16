"""Pydantic schemas for the Wiki Brain API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Wiki Page schemas
# ---------------------------------------------------------------------------

class WikiPageBase(BaseModel):
    """Shared base fields for wiki page create/update."""

    title: str = Field(..., max_length=500, description="Page title")
    summary: str | None = Field(None, description="Short human-readable summary")
    content: dict[str, Any] | None = Field(
        None,
        description=(
            "Structured content dict with keys: background, causes, main_events, "
            "results, significance, people, timeline, references"
        ),
    )
    status: str = Field(
        "draft",
        description="Lifecycle status: draft | pending_review | approved | published",
    )
    event_type: str | None = Field(
        None,
        description="Event category: military | diplomatic | political | cultural",
    )
    period: str | None = Field(None, description="Historical period, e.g. '1945-1954'")
    start_year: int | None = Field(None, description="Start year of the event")
    end_year: int | None = Field(None, description="End year of the event")
    source_document_ids: list[str] | None = Field(
        None, description="UUIDs of source documents used to generate this page"
    )
    project_id: str | None = Field(
        None, description="Project UUID scoping the wiki page"
    )


class WikiPageCreate(WikiPageBase):
    """Schema for creating a wiki page manually."""

    slug: str | None = Field(
        None,
        max_length=500,
        description="URL slug — auto-generated from title if omitted",
    )


class WikiPageUpdate(BaseModel):
    """Schema for updating a wiki page. All fields optional."""

    model_config = ConfigDict(from_attributes=True)

    title: str | None = Field(None, max_length=500)
    summary: str | None = None
    content: dict[str, Any] | None = None
    status: str | None = None
    event_type: str | None = None
    period: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    source_document_ids: list[str] | None = None
    project_id: str | None = None
    change_summary: str | None = Field(
        None, description="Brief description of what changed in this edit"
    )


class WikiPageResponse(WikiPageBase):
    """Full wiki page response including server-generated fields."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    version: int
    created_by: str | None
    created_at: datetime
    updated_at: datetime


class WikiPageListResponse(BaseModel):
    """Paginated list of wiki pages."""

    model_config = ConfigDict(from_attributes=True)

    pages: list[WikiPageResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Wiki Page Version schemas
# ---------------------------------------------------------------------------

class WikiPageVersionResponse(BaseModel):
    """Version snapshot of a wiki page."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    wiki_page_id: str
    version: int
    content_snapshot: dict[str, Any] | None
    change_summary: str | None
    created_by: str | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Brain Build Job schemas
# ---------------------------------------------------------------------------

class BrainBuildJobResponse(BaseModel):
    """Full build job response."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    job_type: str
    status: str
    source_document_ids: list[str] | None
    result_summary: dict[str, Any] | None
    error_message: str | None
    logs: list[Any]
    created_by: str | None
    started_at: datetime | None
    finished_at: datetime | None
    created_at: datetime


class BrainBuildJobListResponse(BaseModel):
    """Paginated list of build jobs."""

    model_config = ConfigDict(from_attributes=True)

    jobs: list[BrainBuildJobResponse]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# Brain Review Plan schemas
# ---------------------------------------------------------------------------

class BrainReviewPlanResponse(BaseModel):
    """Review plan with proposed pages."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    job_id: str
    proposed_pages: list[Any]
    status: str
    admin_notes: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime


class BrainReviewPlanListResponse(BaseModel):
    """List of review plans (typically used for pending queue)."""

    model_config = ConfigDict(from_attributes=True)

    plans: list[BrainReviewPlanResponse]
    total: int


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------

class StartBuildJobRequest(BaseModel):
    """Request body for starting a new wiki brain build job."""

    document_ids: list[str] = Field(
        ...,
        min_length=1,
        description="List of document UUIDs to process through the wiki pipeline",
    )


class ApproveReviewPlanRequest(BaseModel):
    """Request body for approving or rejecting a review plan."""

    notes: str | None = Field(
        None,
        description="Optional admin notes / rationale for the decision",
    )
