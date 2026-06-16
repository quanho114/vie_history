"""Project and Project Workspace scoping models."""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
    func,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Project(Base):
    """A research project workspace scoping wiki pages and sources."""

    __tablename__ = "projects"
    __table_args__ = (
        Index("idx_projects_slug", "slug"),
        Index("idx_projects_created_at", "created_at"),
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
    name: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    creator: Mapped["User | None"] = relationship("User", foreign_keys=[created_by])
    members: Mapped[list["ProjectMember"]] = relationship(
        "ProjectMember",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    sources: Mapped[list["ProjectSource"]] = relationship(
        "ProjectSource",
        back_populates="project",
        cascade="all, delete-orphan",
    )
    wiki_pages: Mapped[list["WikiPage"]] = relationship(
        "WikiPage",
        back_populates="project",
    )
    drafts: Mapped[list["WikiPageDraft"]] = relationship(
        "WikiPageDraft",
        back_populates="project",
    )

    def __repr__(self) -> str:
        return f"<Project slug={self.slug} name={self.name[:50]}>"


class ProjectMember(Base):
    """Membership mapping for users belonging to projects with scoped roles."""

    __tablename__ = "project_members"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_members_project_user"),
        Index("idx_project_members_project", "project_id"),
        Index("idx_project_members_user", "user_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Role in project: viewer, contributor, editor, admin
    role: Mapped[str] = mapped_column(String(50), default="viewer", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="members")
    user: Mapped["User"] = relationship("User")

    def __repr__(self) -> str:
        return f"<ProjectMember project={self.project_id} user={self.user_id} role={self.role}>"


class ProjectSource(Base):
    """Links a Document to a Project workspace."""

    __tablename__ = "project_sources"
    __table_args__ = (
        UniqueConstraint("project_id", "document_id", name="uq_project_sources_project_doc"),
        Index("idx_project_sources_project", "project_id"),
        Index("idx_project_sources_doc", "document_id"),
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    project_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="sources")
    document: Mapped["Document"] = relationship("Document")

    def __repr__(self) -> str:
        return f"<ProjectSource project={self.project_id} doc={self.document_id}>"
