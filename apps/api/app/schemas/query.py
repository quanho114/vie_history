"""Query schemas."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class QueryRequest(BaseModel):
    """Query request with Pydantic V2 features."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        use_enum_values=True,
        json_schema_extra={
            "example": {
                "query": "Chiến tranh Việt Nam",
                "project_id": "optional-uuid",
                "max_chunks": 20,
            }
        },
    )

    query: str = Field(
        ...,
        min_length=2,
        max_length=1000,
        description="User query text",
        examples=["Chiến tranh Việt Nam", "Đại hội Đảng Lao Động"],
    )
    project_id: str | None = Field(default=None, description="Optional project filter")
    session_id: str | None = Field(default=None, description="Optional session ID")
    max_chunks: Annotated[int, Field(ge=1, le=100, description="Max chunks to retrieve")] = 20
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    stream: bool = Field(default=True, description="Enable streaming response")
    filters: dict | None = Field(
        default=None,
        description="Optional filters: year_range, person, event, topic",
    )
    mode: str | None = Field(
        default=None,
        description="Force specific mode: factual, timeline, compare, summary, source_audit",
    )

    @field_validator("query")
    @classmethod
    def query_must_not_be_empty(cls, v: str) -> str:
        """Ensure query is not just whitespace."""
        if not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v.strip()

    @model_validator(mode="after")
    def validate_query_context(self) -> "QueryRequest":
        """Cross-field validation."""
        if self.max_chunks < 5 and len(self.query) > 500:
            # Warn but don't fail - it's a valid config
            pass
        return self


class QueryConfig(BaseModel):
    """Query execution configuration with defaults."""
    model_config = ConfigDict(extra="forbid")

    max_chunks: int = 20
    temperature: float = 0.7
    stream: bool = True
    include_sources: bool = True
    include_trace: bool = False

    @classmethod
    def from_request(cls, req: QueryRequest) -> "QueryConfig":
        return cls(
            max_chunks=req.max_chunks,
            temperature=req.temperature or 0.7,
            stream=req.stream,
        )


class CitationSource(BaseModel):
    """Schema for citation source."""

    document_id: str
    document_title: str
    source_url: str | None = None
    chunk_id: str
    section_title: str | None = None
    excerpt: str
    score: float = 0.0


class VerificationResult(BaseModel):
    """Schema for verification result."""

    sufficient_evidence: bool
    evidence_count: int
    duplicate_ratio: float = 0.0
    conflict_detected: bool = False
    message: str | None = None


class ResponseTrace(BaseModel):
    """Schema for response trace."""

    intent: str
    workflow: str
    tools_used: list[str] = Field(default_factory=list)
    retrieval_ms: int = 0
    generation_ms: int = 0
    cache_hit: bool = False
    verification: VerificationResult | None = None


class QueryResponse(BaseModel):
    """Schema for query response."""

    session_id: str
    message_id: str
    mode: str
    answer: str
    citations: list[CitationSource] = Field(default_factory=list)
    trace: ResponseTrace


class QueryStreamChunk(BaseModel):
    """Schema for SSE stream chunk."""

    type: str = Field(..., description="Chunk type: token, citation, trace, done")
    data: str | dict
