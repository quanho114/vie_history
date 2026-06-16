"""Admin routes."""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.rbac import Permission, has_permission
from app.core.security import AdminUser, get_password_hash
from app.models.document import Document
from app.models.ingest_job import IngestJob
from app.models.user import User
from app.schemas.document import DocumentResponse
from app.services.ingestion.service import IngestService


router = APIRouter()
ingest_service = IngestService()


@router.get("/stats")
async def get_admin_stats(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Get admin statistics — all counts fetched in parallel for speed."""
    if not has_permission(getattr(admin, 'role', 'user'), Permission.ADMIN_STATS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    # Single query per resource to minimize round-trips
    doc_stats = await db.execute(
        select(
            func.count(Document.id),
            func.count().filter(Document.status == "pending"),
            func.count().filter(Document.status == "approved"),
            func.count().filter(Document.status == "rejected"),
        ).select_from(Document)
    )
    doc_row = doc_stats.one()
    job_stats = await db.execute(
        select(
            func.count(IngestJob.id),
            func.count().filter(IngestJob.status == "queued"),
            func.count().filter(IngestJob.status == "running"),
            func.count().filter(IngestJob.status == "failed"),
        ).select_from(IngestJob)
    )
    job_row = job_stats.one()

    return {
        "documents": {
            "total": doc_row[0] or 0,
            "pending": doc_row[1] or 0,
            "approved": doc_row[2] or 0,
            "rejected": doc_row[3] or 0,
        },
        "jobs": {
            "total": job_row[0] or 0,
            "queued": job_row[1] or 0,
            "running": job_row[2] or 0,
            "failed": job_row[3] or 0,
        },
    }


@router.get("/quality-report")
async def get_quality_report(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Get document quality report."""
    if not has_permission(getattr(admin, 'role', 'user'), Permission.ADMIN_STATS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    # Get documents with quality scores
    result = await db.execute(
        select(Document)
        .where(Document.status == "approved")
        .order_by(Document.quality_score.desc())
        .limit(100)
    )
    documents = result.scalars().all()

    avg_quality = (
        sum(d.quality_score for d in documents) / len(documents)
        if documents else 0
    )

    return {
        "average_quality_score": round(avg_quality, 2),
        "documents_by_quality": {
            "high": len([d for d in documents if d.quality_score >= 0.8]),
            "medium": len([d for d in documents if 0.5 <= d.quality_score < 0.8]),
            "low": len([d for d in documents if d.quality_score < 0.5]),
        },
        "top_documents": [
            {
                "id": d.id,
                "title": d.title,
                "quality_score": d.quality_score,
            }
            for d in documents[:10]
        ],
    }


@router.post("/documents/{document_id}/approve", response_model=DocumentResponse)
async def approve_document(
    document_id: str,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Approve a document for indexing."""
    if not has_permission(getattr(admin, 'role', 'user'), Permission.DOCUMENT_APPROVE):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    document.status = "approved"
    await db.commit()
    await db.refresh(document)

    await ingest_service.reindex_document(db=db, document=document)

    return DocumentResponse.model_validate(document)


@router.post("/documents/{document_id}/reject", response_model=DocumentResponse)
async def reject_document(
    document_id: str,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Reject a document."""
    if not has_permission(getattr(admin, 'role', 'user'), Permission.DOCUMENT_APPROVE):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    document.status = "rejected"
    await db.commit()
    await db.refresh(document)

    return DocumentResponse.model_validate(document)


@router.post("/documents/{document_id}/reindex")
async def reindex_document(
    document_id: str,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Trigger document reindexing."""
    if not has_permission(getattr(admin, 'role', 'user'), Permission.ADMIN_STATS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    indexed = await ingest_service.reindex_document(db=db, document=document)
    return {
        "status": "reindexed" if indexed else "reindex_failed",
        "document_id": document_id,
    }


# === USER MANAGEMENT ENDPOINTS ===

class AdminUserResponse(BaseModel):
    id: str
    email: str
    username: str
    role: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class AdminResetPasswordRequest(BaseModel):
    new_password: str = Field(..., min_length=8)

@router.get("/users", response_model=list[AdminUserResponse])
async def list_users(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """List all users (admin only)."""
    if not has_permission(getattr(admin, 'role', 'user'), Permission.ADMIN_USERS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return users

@router.post("/users/{user_id}/reset-password")
async def reset_user_password(
    user_id: str,
    data: AdminResetPasswordRequest,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Reset a user's password (admin only)."""
    if not has_permission(getattr(admin, 'role', 'user'), Permission.ADMIN_USERS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.hashed_password = get_password_hash(data.new_password)
    await db.commit()

    return {"status": "success", "message": f"Password reset successfully for user {user.username}"}


from app.models.reset_request import ResetRequest

class ResetRequestAdminResponse(BaseModel):
    id: str
    email: str
    username: str | None
    reason: str | None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

@router.get("/reset-requests", response_model=list[ResetRequestAdminResponse])
async def list_reset_requests(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """List all password reset requests (admin only)."""
    if not has_permission(getattr(admin, 'role', 'user'), Permission.ADMIN_USERS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    result = await db.execute(select(ResetRequest).order_by(ResetRequest.created_at.desc()))
    reqs = result.scalars().all()
    return reqs

class ApproveResetRequest(BaseModel):
    new_password: str = Field(..., min_length=8)


# === BM25 INDEX MANAGEMENT ===

@router.post("/bm25/rebuild")
async def rebuild_bm25_index(
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Trigger a full BM25 index rebuild from all indexed document chunks."""
    if not has_permission(getattr(admin, 'role', 'user'), Permission.ADMIN_STATS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    from app.services.retrieval.bm25_index import build_bm25_index, get_bm25_index

    index = await build_bm25_index(db)
    return {
        "status": "rebuilt",
        "num_chunks": index.size,
    }


@router.get("/bm25/stats")
async def get_bm25_stats(
    admin: AdminUser,
):
    """Return current BM25 index statistics."""
    if not has_permission(getattr(admin, 'role', 'user'), Permission.ADMIN_STATS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    from app.services.retrieval.bm25_index import get_bm25_index

    index = get_bm25_index()
    if index is None:
        return {"status": "not_initialized", "num_chunks": 0}

    return {
        "status": "ready",
        "num_chunks": index.size,
    }


@router.post("/bm25/add/{chunk_id}")
async def add_chunk_to_bm25(
    chunk_id: str,
    content: str,
    admin: AdminUser,
):
    """Incrementally add a single chunk to the BM25 index without full rebuild."""
    if not has_permission(getattr(admin, 'role', 'user'), Permission.ADMIN_STATS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    from app.services.retrieval.bm25_index import get_bm25_index

    index = get_bm25_index()
    if index is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="BM25 index not initialized",
        )

    index.add_chunk({"id": chunk_id, "content": content})
    return {"status": "added", "chunk_id": chunk_id, "total_chunks": index.size}


@router.delete("/bm25/remove/{chunk_id}")
async def remove_chunk_from_bm25(
    chunk_id: str,
    admin: AdminUser,
):
    """Remove a chunk from the BM25 index."""
    if not has_permission(getattr(admin, 'role', 'user'), Permission.ADMIN_STATS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    from app.services.retrieval.bm25_index import get_bm25_index

    index = get_bm25_index()
    if index is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="BM25 index not initialized",
        )

    index.remove_chunk(chunk_id)
    return {"status": "removed", "chunk_id": chunk_id, "total_chunks": index.size}


@router.post("/reset-requests/{request_id}/approve")
async def approve_reset_request(
    request_id: str,
    data: ApproveResetRequest,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Approve a reset request, reset user password, and set request status to approved (admin only)."""
    if not has_permission(getattr(admin, 'role', 'user'), Permission.ADMIN_USERS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    req_result = await db.execute(select(ResetRequest).where(ResetRequest.id == request_id))
    req = req_result.scalar_one_or_none()
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reset request not found",
        )
        
    user_result = await db.execute(select(User).where(User.email == req.email))
    user = user_result.scalar_one_or_none()
    if user is None:
        req.status = "failed"
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User belonging to this email was not found",
        )
        
    user.hashed_password = get_password_hash(data.new_password)
    req.status = "approved"
    await db.commit()
    return {"status": "success", "message": f"Mật khẩu đã đặt lại thành công cho người dùng {user.username}"}

@router.post("/reset-requests/{request_id}/reject")
async def reject_reset_request(
    request_id: str,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
):
    """Reject a password reset request (admin only)."""
    if not has_permission(getattr(admin, 'role', 'user'), Permission.ADMIN_USERS):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
    req_result = await db.execute(select(ResetRequest).where(ResetRequest.id == request_id))
    req = req_result.scalar_one_or_none()
    if req is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reset request not found",
        )
        
    req.status = "rejected"
    await db.commit()
    return {"status": "success", "message": "Đã từ chối yêu cầu đặt lại mật khẩu"}

