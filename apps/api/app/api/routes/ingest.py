"""Ingestion routes."""

from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from fastapi.responses import JSONResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import CurrentUser
from app.core.audit import get_audit_logger, AuditAction, AuditEvent
from app.models.document import Document
from app.models.ingest_job import IngestJob
from app.schemas.ingest import (
    IngestURLRequest,
    IngestJobResponse,
    IngestJobListResponse,
    IngestPreviewResponse,
)
from app.services.ingestion.service import IngestService
from app.services.ingestion.url_validator import URLValidator


router = APIRouter()
ingest_service = IngestService()
url_validator = URLValidator()


@router.post("", status_code=status.HTTP_202_ACCEPTED)
async def ingest_url_alias(
    data: IngestURLRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Compatibility alias for POST /api/v1/ingest."""
    validation = url_validator.validate(data.url)
    if not validation["valid"]:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=validation["error"],
        )
    return await ingest_url(data=data, current_user=current_user, db=db)


@router.post("/url", status_code=status.HTTP_202_ACCEPTED)
async def ingest_url(
    data: IngestURLRequest,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Ingest a URL asynchronously in the background.

    The operation creates a job in the database with status 'queued' and adds it to the sequential
    background processing queue, returning immediately.
    """
    job = IngestJob(
        source_input=data.url,
        source_type="url",
        status="queued",
        stage="queued",
    )
    job.add_log("Ingestion queued")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Queue the job for background worker
    from app.services.ingestion.queue import ingestion_queue_manager
    await ingestion_queue_manager.add_job(
        job_id=job.id,
        user_id=current_user.id,
        tags=data.tags,
    )

    get_audit_logger().log(AuditEvent(
        action=AuditAction.INGEST_START,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=getattr(current_user, 'role', 'user'),
        resource_type="ingestion",
        details={"url": data.url[:200], "job_id": job.id},
    ))
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "job_id": job.id,
            "status": job.status,
            "stage": job.stage,
            "document_id": job.document_id,
            "error_message": job.error_message,
        },
    )


@router.post("/file", status_code=status.HTTP_202_ACCEPTED)
async def ingest_file(
    current_user: CurrentUser,
    upload: UploadFile = File(...),
    tags: str | None = Form(default=None),
    db: AsyncSession = Depends(get_db),
):
    """Ingest a text/markdown/PDF file asynchronously in the background."""
    storage_dir = Path("storage/uploads")
    storage_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "upload").suffix
    file_name = f"{uuid4()}{suffix}"
    file_path = storage_dir / file_name
    file_path.write_bytes(await upload.read())

    parsed_tags = [tag.strip() for tag in (tags or "").split(",") if tag.strip()]

    job = IngestJob(
        source_input=upload.filename or file_name,
        source_type="file",
        status="queued",
        stage="queued",
    )
    job.add_log("File upload completed, ingestion queued")
    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Queue the job for background worker
    from app.services.ingestion.queue import ingestion_queue_manager
    await ingestion_queue_manager.add_job(
        job_id=job.id,
        user_id=current_user.id,
        tags=parsed_tags,
        file_path=str(file_path),
        content_type=upload.content_type,
    )

    get_audit_logger().log(AuditEvent(
        action=AuditAction.INGEST_START,
        actor_id=current_user.id,
        actor_email=current_user.email,
        actor_role=getattr(current_user, 'role', 'user'),
        resource_type="ingestion",
        details={"filename": upload.filename or file_name, "job_id": job.id},
    ))
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "job_id": job.id,
            "status": job.status,
            "stage": job.stage,
            "document_id": job.document_id,
            "error_message": job.error_message,
        },
    )



@router.get("/jobs", response_model=IngestJobListResponse)
async def list_ingest_jobs(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
):
    """List ingestion jobs."""
    query = select(IngestJob)

    if status:
        query = query.where(IngestJob.status == status)

    # Count total
    count_query = select(func.count(IngestJob.id))
    if status:
        count_query = count_query.where(IngestJob.status == status)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Get jobs
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(IngestJob.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    jobs = result.scalars().all()

    return IngestJobListResponse(
        jobs=[IngestJobResponse.model_validate(j) for j in jobs],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/jobs/{job_id}", response_model=IngestJobResponse)
async def get_ingest_job(
    job_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Get ingestion job by ID."""
    result = await db.execute(
        select(IngestJob).where(IngestJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    return IngestJobResponse.model_validate(job)


@router.post("/jobs/{job_id}/retry", response_model=IngestJobResponse)
async def retry_ingest_job(
    job_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Retry a failed ingestion job."""
    result = await db.execute(
        select(IngestJob).where(IngestJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.status not in ("failed", "done"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only retry failed or done jobs",
        )

    retried = await ingest_service.retry_job(db=db, job=job, user_id=current_user.id)
    return IngestJobResponse.model_validate(retried)


@router.get("/preview/{job_id}", response_model=IngestPreviewResponse)
async def get_ingest_preview(
    job_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """
    Get ingestion preview for admin approval.
    Shows cleaned markdown and metadata.
    """
    result = await db.execute(
        select(IngestJob).where(IngestJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    if job.document_id:
        doc_result = await db.execute(
            select(Document).where(Document.id == job.document_id)
        )
        document = doc_result.scalar_one_or_none()

        if document:
            # Load markdown content
            markdown_content = None
            if document.markdown_content_path:
                try:
                    import aiofiles
                    async with aiofiles.open(document.markdown_content_path, "r", encoding="utf-8") as f:
                        markdown_content = await f.read()
                except Exception:
                    pass

            return IngestPreviewResponse(
                job_id=job.id,
                document_id=document.id,
                title=document.title,
                markdown_content=markdown_content or "",
                metadata={
                    "source_url": document.source_url,
                    "source_domain": document.source_domain,
                    "source_type": document.source_type,
                    "author": document.author,
                    "tags": document.tags,
                    "detected_years": document.detected_years,
                    "entity_persons": document.entity_persons,
                    "entity_places": document.entity_places,
                    "entity_organizations": document.entity_organizations,
                    "entity_events": document.entity_events,
                },
                quality_score=document.quality_score,
                duplicate_warning=False,
                suggested_tags=document.tags or [],
            )

    return IngestPreviewResponse(
        job_id=job.id,
        document_id=None,
        title="Processing...",
        markdown_content="Document is still being processed.",
        metadata={},
        quality_score=0.0,
        duplicate_warning=False,
        suggested_tags=[],
    )


@router.delete("/jobs", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_ingest_jobs(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Delete all ingestion job history entries."""
    from sqlalchemy import delete
    await db.execute(delete(IngestJob))
    await db.commit()
    return None


@router.delete("/jobs/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ingest_job(
    job_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Delete an ingestion job history entry."""
    result = await db.execute(
        select(IngestJob).where(IngestJob.id == job_id)
    )
    job = result.scalar_one_or_none()

    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )

    await db.delete(job)
    await db.commit()
    return None

