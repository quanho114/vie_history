"""Document schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    """Base document schema."""

    title: str
    source_url: str | None = None
    source_type: str | None = None
    author: str | None = None
    summary: str | None = None
    tags: list[str] | None = None


class DocumentCreate(DocumentBase):
    """Schema for creating a document."""

    canonical_url: str | None = None
    source_domain: str | None = None
    markdown_content: str | None = None


class DocumentUpdate(BaseModel):
    """Schema for updating a document."""

    title: str | None = None
    status: str | None = None
    summary: str | None = None
    tags: list[str] | None = None


class DocumentChunkResponse(BaseModel):
    """Schema for document chunk response."""

    id: str
    document_id: str
    chunk_index: int
    section_title: str | None = None
    content: str
    token_count: int | None = None

    model_config = {"from_attributes": True}


class DocumentResponse(BaseModel):
    """Schema for document response."""

    id: str
    title: str
    source_url: str | None = None
    source_domain: str | None = None
    source_type: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    language: str
    summary: str | None = None
    tags: list[str] | None = None
    detected_years: list[int] | None = None
    entity_persons: list[str] | None = None
    entity_places: list[str] | None = None
    entity_organizations: list[str] | None = None
    entity_events: list[str] | None = None
    status: str
    quality_score: float
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentDetailResponse(DocumentResponse):
    """Schema for detailed document response."""

    markdown_content: str | None = None
    chunk_count: int = 0


class DocumentListResponse(BaseModel):
    """Schema for document list response."""

    documents: list[DocumentResponse]
    total: int
    page: int
    page_size: int
