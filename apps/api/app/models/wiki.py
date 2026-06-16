"""Wiki Brain models — Wikipedia-style knowledge pages generated from ingested documents."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    String,
    Text,
    DateTime,
    Float,
    Integer,
    Boolean,
    ForeignKey,
    Index,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WikiPage(Base):
    """A structured wiki-style knowledge page generated from ingested historical documents."""

    __tablename__ = "wiki_pages"
    __table_args__ = (
        Index("idx_wiki_pages_slug", "slug"),
        Index("idx_wiki_pages_status", "status"),
        Index("idx_wiki_pages_period", "period"),
        Index("idx_wiki_pages_event_type", "event_type"),
        Index("idx_wiki_pages_project_slug", "project_id", "slug"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    slug: Mapped[str] = mapped_column(
        String(500),
        unique=True,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Structured content with sections: background, causes, main_events, results,
    # significance, people, timeline, references
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    # Lifecycle status: draft → pending_review → approved → published
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    event_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    period: Mapped[str | None] = mapped_column(String(50), nullable=True)
    start_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Array of document UUIDs (denormalized for performance)
    source_document_ids: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    created_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    creator: Mapped["User | None"] = relationship("User", foreign_keys=[created_by])
    project: Mapped["Project | None"] = relationship("Project", back_populates="wiki_pages")
    versions: Mapped[list["WikiPageVersion"]] = relationship(
        "WikiPageVersion",
        back_populates="wiki_page",
        cascade="all, delete-orphan",
        order_by="WikiPageVersion.version",
    )
    links_from: Mapped[list["WikiLink"]] = relationship(
        "WikiLink",
        foreign_keys="WikiLink.source_page_id",
        back_populates="source_page",
        cascade="all, delete-orphan",
    )
    claims: Mapped[list["WikiClaim"]] = relationship(
        "WikiClaim",
        back_populates="wiki_page",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<WikiPage slug={self.slug} v{self.version}>"


class WikiPageVersion(Base):
    """Immutable version snapshot of a WikiPage for audit / rollback."""

    __tablename__ = "wiki_page_versions"
    __table_args__ = (
        UniqueConstraint("wiki_page_id", "version", name="uq_wiki_page_version"),
        Index("idx_wiki_page_versions_wiki_page_id", "wiki_page_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    wiki_page_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("wiki_pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    # Full JSONB snapshot of the page content at this version
    content_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    wiki_page: Mapped["WikiPage"] = relationship("WikiPage", back_populates="versions")

    def __repr__(self) -> str:
        return f"<WikiPageVersion page={self.wiki_page_id} v{self.version}>"


class WikiLink(Base):
    """Directional link between two wiki pages indicating a semantic relationship."""

    __tablename__ = "wiki_links"
    __table_args__ = (
        Index("idx_wiki_links_source", "source_page_id"),
        Index("idx_wiki_links_target", "target_page_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    source_page_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("wiki_pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_page_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("wiki_pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Link semantics: related | caused_by | led_to | part_of
    link_type: Mapped[str] = mapped_column(String(50), default="related", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    source_page: Mapped["WikiPage"] = relationship(
        "WikiPage",
        foreign_keys=[source_page_id],
        back_populates="links_from",
    )
    target_page: Mapped["WikiPage"] = relationship(
        "WikiPage",
        foreign_keys=[target_page_id],
    )

    def __repr__(self) -> str:
        return f"<WikiLink {self.source_page_id} --{self.link_type}--> {self.target_page_id}>"


class WikiClaim(Base):
    """A verifiable factual claim extracted from a wiki page section."""

    __tablename__ = "wiki_claims"
    __table_args__ = (
        Index("idx_wiki_claims_wiki_page_id", "wiki_page_id"),
        Index("idx_wiki_claims_verified", "verified"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    wiki_page_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("wiki_pages.id", ondelete="CASCADE"),
        nullable=False,
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    # Section of the wiki page this claim originates from
    section: Mapped[str | None] = mapped_column(String(100), nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    wiki_page: Mapped["WikiPage"] = relationship("WikiPage", back_populates="claims")
    sources: Mapped[list["WikiSource"]] = relationship(
        "WikiSource",
        back_populates="claim",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<WikiClaim page={self.wiki_page_id} verified={self.verified}>"


class WikiSource(Base):
    """A document chunk that supports a WikiClaim, with an excerpt and relevance score."""

    __tablename__ = "wiki_sources"
    __table_args__ = (
        Index("idx_wiki_sources_claim_id", "wiki_claim_id"),
        Index("idx_wiki_sources_document_id", "document_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    wiki_claim_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("wiki_claims.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    chunk_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("document_chunks.id", ondelete="SET NULL"),
        nullable=True,
    )
    excerpt: Mapped[str | None] = mapped_column(Text, nullable=True)
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    claim: Mapped["WikiClaim"] = relationship("WikiClaim", back_populates="sources")

    def __repr__(self) -> str:
        return f"<WikiSource claim={self.wiki_claim_id} doc={self.document_id}>"


class BrainBuildJob(Base):
    """Background job that orchestrates the wiki-brain pipeline over a set of documents."""

    __tablename__ = "brain_build_jobs"
    __table_args__ = (
        Index("idx_brain_build_jobs_status", "status"),
        Index("idx_brain_build_jobs_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    # Job category: wiki_build | timeline_extract | graph_extract
    job_type: Mapped[str] = mapped_column(String(50), default="wiki_build", nullable=False)
    # Lifecycle: pending → running → awaiting_review → done | failed
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    source_document_ids: Mapped[list[str] | None] = mapped_column(
        ARRAY(String), nullable=True
    )
    result_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    logs: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    created_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    review_plan: Mapped["BrainReviewPlan | None"] = relationship(
        "BrainReviewPlan",
        back_populates="job",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<BrainBuildJob type={self.job_type} status={self.status}>"


class BrainReviewPlan(Base):
    """Admin review gate: proposed wiki pages from a BrainBuildJob awaiting approval."""

    __tablename__ = "brain_review_plans"
    __table_args__ = (
        Index("idx_brain_review_plans_status", "status"),
        Index("idx_brain_review_plans_job_id", "job_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    job_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("brain_build_jobs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    # List of proposed wiki page drafts (dicts with title, slug, summary, content outline)
    proposed_pages: Mapped[list] = mapped_column(JSONB, nullable=False)
    # Status: pending | approved | rejected | partial
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    job: Mapped["BrainBuildJob"] = relationship(
        "BrainBuildJob", back_populates="review_plan"
    )

    def __repr__(self) -> str:
        return f"<BrainReviewPlan job={self.job_id} status={self.status}>"


class WikiPageDraft(Base):
    """A proposed edit or creation of a WikiPage awaiting approval."""

    __tablename__ = "wiki_page_drafts"
    __table_args__ = (
        Index("idx_wiki_page_drafts_status", "status"),
        Index("idx_wiki_page_drafts_project", "project_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    wiki_page_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("wiki_pages.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    slug: Mapped[str] = mapped_column(String(500), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending | approved | rejected
    admin_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    proposed_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    wiki_page: Mapped["WikiPage | None"] = relationship("WikiPage", foreign_keys=[wiki_page_id])
    project: Mapped["Project | None"] = relationship("Project", back_populates="drafts")
    proposer: Mapped["User | None"] = relationship("User", foreign_keys=[proposed_by])
    reviewer: Mapped["User | None"] = relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self) -> str:
        return f"<WikiPageDraft slug={self.slug} status={self.status}>"

