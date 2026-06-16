"""API routes for Project Workspaces."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser, AdminUser
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectListResponse,
    ProjectUpdate,
)
from app.services.project.project_service import ProjectService

router = APIRouter()
project_service = ProjectService()


@router.get("", response_model=ProjectListResponse, summary="List project workspaces")
async def list_projects(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ProjectListResponse:
    """Retrieve all available project workspaces."""
    projects, total = await project_service.get_projects(db, page=page, page_size=page_size)
    return ProjectListResponse(
        projects=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
    )


@router.get("/{slug}", response_model=ProjectResponse, summary="Get project by slug")
async def get_project(
    slug: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Retrieve a project workspace by its unique slug."""
    project = await project_service.get_project_by_slug(db, slug)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project with slug '{slug}' not found",
        )
    return ProjectResponse.model_validate(project)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create project workspace",
)
async def create_project(
    data: ProjectCreate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
) -> ProjectResponse:
    """Create a new project workspace.

    The user who creates the project is automatically added as an admin member.
    """
    project = await project_service.create_project(
        db,
        data=data.model_dump(exclude_unset=False),
        created_by_id=current_user.id,
    )
    return ProjectResponse.model_validate(project)
