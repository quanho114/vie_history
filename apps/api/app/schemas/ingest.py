"""Ingestion schemas."""

from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class IngestURLRequest(BaseModel):
    """Schema for URL ingestion request."""

    url: str = Field(..., description="URL to ingest")
    tags: list[str] | None = Field(
        default=None,
        description="Optional tags for the document",
    )
    period_hint: str | None = Field(
        default=None,
        description="Optional period hint (e.g., '1945-1975')",
    )


class IngestFileRequest(BaseModel):
    """Schema for file ingestion request."""

    file_type: str = Field(..., description="File type: pdf, docx, txt, md")
    tags: list[str] | None = None
    period_hint: str | None = None


class IngestJobResponse(BaseModel):
    """Schema for ingestion job response."""

    id: str
    source_input: str
    source_type: str
    status: str
    stage: str | None = None
    error_message: str | None = None
    logs: list[dict] = Field(default_factory=list)
    document_id: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class IngestPreviewResponse(BaseModel):
    """Schema for ingestion preview (admin approval)."""

    job_id: str
    document_id: str | None = None
    title: str
    markdown_content: str
    metadata: dict
    quality_score: float
    duplicate_warning: bool = False
    suggested_tags: list[str] = Field(default_factory=list)


class IngestJobListResponse(BaseModel):
    """Schema for ingestion job list."""

    jobs: list[IngestJobResponse]
    total: int
    page: int
    page_size: int
