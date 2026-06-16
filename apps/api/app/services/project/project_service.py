"""ProjectService — CRUD operations for project workspaces and project members."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models.project import Project, ProjectMember, ProjectSource
from app.services.wiki.wiki_service import _slugify_basic

logger = get_logger("project_service")


class ProjectService:
    """CRUD service for project workspaces."""

    async def get_projects(
        self,
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Project], int]:
        """Fetch list of all projects, ordered by updated_at descending."""
        query = select(Project)
        count_query = select(func.count(Project.id))

        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        result = await db.execute(
            query.order_by(Project.updated_at.desc()).offset(offset).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_project_by_slug(self, db: AsyncSession, slug: str) -> Project | None:
        """Fetch project by slug."""
        result = await db.execute(select(Project).where(Project.slug == slug))
        return result.scalar_one_or_none()

    async def get_project(self, db: AsyncSession, project_id: str) -> Project | None:
        """Fetch project by ID."""
        result = await db.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()

    async def create_project(
        self,
        db: AsyncSession,
        data: dict,
        created_by_id: str | None = None,
    ) -> Project:
        """Create a new project workspace and make creator the first admin member."""
        slug = data.get("slug") or _slugify_basic(data["name"])

        # Check for slug uniqueness
        existing = await db.execute(select(Project).where(Project.slug == slug))
        if existing.scalar_one_or_none():
            slug = f"{slug}-{str(uuid4())[:8]}"

        project = Project(
            id=str(uuid4()),
            slug=slug,
            name=data["name"],
            description=data.get("description"),
            created_by=created_by_id,
        )
        db.add(project)
        await db.flush()

        if created_by_id:
            member = ProjectMember(
                id=str(uuid4()),
                project_id=project.id,
                user_id=created_by_id,
                role="admin",
            )
            db.add(member)

        await db.commit()
        await db.refresh(project)
        logger.info("project_created", slug=project.slug, project_id=project.id)
        return project

    async def get_project_members(self, db: AsyncSession, project_id: str) -> list[ProjectMember]:
        """Fetch all members of a project."""
        result = await db.execute(select(ProjectMember).where(ProjectMember.project_id == project_id))
        return list(result.scalars().all())

    async def add_project_member(
        self,
        db: AsyncSession,
        project_id: str,
        user_id: str,
        role: str = "viewer",
    ) -> ProjectMember:
        """Add user to project or update their role if they are already in the project."""
        result = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if member:
            member.role = role
        else:
            member = ProjectMember(
                id=str(uuid4()),
                project_id=project_id,
                user_id=user_id,
                role=role,
            )
            db.add(member)

        await db.commit()
        await db.refresh(member)
        return member

    async def remove_project_member(self, db: AsyncSession, project_id: str, user_id: str) -> bool:
        """Remove a member from a project."""
        result = await db.execute(
            select(ProjectMember).where(
                ProjectMember.project_id == project_id,
                ProjectMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        if not member:
            return False
        await db.delete(member)
        await db.commit()
        return True
