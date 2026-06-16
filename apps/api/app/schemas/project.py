"""Pydantic schemas for the Projects and Drafts API."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Project schemas
# ---------------------------------------------------------------------------

class ProjectBase(BaseModel):
    """Shared base fields for projects."""

    name: str = Field(..., max_length=500, description="Project name")
    description: str | None = Field(None, description="Detailed description of the project workspace")


class ProjectCreate(ProjectBase):
    """Schema for creating a project."""

    slug: str | None = Field(
        None,
        max_length=500,
        description="URL slug — auto-generated from name if omitted",
    )


class ProjectUpdate(BaseModel):
    """Schema for updating a project."""

    name: str | None = Field(None, max_length=500)
    description: str | None = None


class ProjectResponse(ProjectBase):
    """Full project response including server-generated fields."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    slug: str
    created_by: str | None
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """List of projects."""

    model_config = ConfigDict(from_attributes=True)

    projects: list[ProjectResponse]
    total: int


# ---------------------------------------------------------------------------
# WikiPageDraft schemas
# ---------------------------------------------------------------------------

class WikiPageDraftBase(BaseModel):
    """Shared base fields for wiki page drafts."""

    wiki_page_id: str | None = Field(None, description="Target WikiPage UUID if this is an edit")
    project_id: str | None = Field(None, description="Project UUID scoping the wiki page")
    slug: str = Field(..., max_length=500, description="Page slug")
    title: str = Field(..., max_length=500, description="Proposed page title")
    summary: str | None = Field(None, description="Proposed summary")
    content: dict[str, Any] | None = Field(
        None,
        description="Proposed structured content dict",
    )
    status: str = Field("pending", description="Draft status: pending | approved | rejected")
    admin_notes: str | None = Field(None, description="Admin review notes")


class WikiPageDraftCreate(BaseModel):
    """Schema for proposing a wiki page draft."""

    wiki_page_id: str | None = Field(None, description="Target WikiPage UUID if this is an edit")
    project_id: str | None = Field(None, description="Project UUID scoping the wiki page")
    title: str = Field(..., max_length=500, description="Proposed page title")
    slug: str | None = Field(None, max_length=500, description="Proposed page slug (auto-generated if omitted)")
    summary: str | None = Field(None, description="Proposed summary")
    content: dict[str, Any] | None = Field(None, description="Proposed content")


class WikiPageDraftReview(BaseModel):
    """Schema for approving or rejecting a proposed draft."""

    status: str = Field(..., description="Action status: approved | rejected")
    admin_notes: str | None = Field(None, description="Optional notes from the reviewer")


class WikiPageDraftResponse(WikiPageDraftBase):
    """Full response schema for a wiki page draft."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    proposed_by: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    created_at: datetime
