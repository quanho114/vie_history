"""Documents routes."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import settings
from app.core.security import get_current_user, CurrentUser
from app.core.audit import get_audit_logger, AuditAction
from app.models.document import Document, DocumentChunk
from app.schemas.document import (
    DocumentResponse,
    DocumentDetailResponse,
    DocumentUpdate,
    DocumentListResponse,
    DocumentChunkResponse,
)


router = APIRouter()


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = None,
    source_type: str | None = None,
    search: str | None = None,
):
    """List all documents."""
    query = select(Document)

    # Apply filters
    if status:
        query = query.where(Document.status == status)
    if source_type:
        query = query.where(Document.source_type == source_type)
    if search:
        query = query.where(Document.title.ilike(f"%{search}%"))

    # Count total
    count_query = select(func.count(Document.id))
    if status:
        count_query = count_query.where(Document.status == status)
    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    # Get documents
    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(Document.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    documents = result.scalars().all()

    get_audit_logger().log_document_access(
        action=AuditAction.DOCUMENT_READ,
        doc_id="bulk",
        user_id=current_user.id,
        email=current_user.email,
        role=getattr(current_user, 'role', 'user'),
        ip_address="",
    )

    return DocumentListResponse(
        documents=[DocumentResponse.model_validate(d) for d in documents],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{document_id}", response_model=DocumentDetailResponse)
async def get_document(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Get document by ID with chunks."""
    result = await db.execute(
        select(Document)
        .where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    get_audit_logger().log_document_access(
        action=AuditAction.DOCUMENT_READ,
        doc_id=document_id,
        user_id=current_user.id,
        email=current_user.email,
        role=getattr(current_user, 'role', 'user'),
        ip_address="",
    )

    # Get chunks
    chunks_result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = chunks_result.scalars().all()

    # Load markdown content if available
    markdown_content = None
    if document.markdown_content_path:
        try:
            import aiofiles
            async with aiofiles.open(document.markdown_content_path, "r", encoding="utf-8") as f:
                markdown_content = await f.read()
        except Exception:
            pass

    return DocumentDetailResponse(
        id=document.id,
        title=document.title,
        source_url=document.source_url,
        source_domain=document.source_domain,
        source_type=document.source_type,
        author=document.author,
        published_at=document.published_at,
        language=document.language,
        summary=document.summary,
        tags=document.tags,
        detected_years=document.detected_years,
        entity_persons=document.entity_persons,
        entity_places=document.entity_places,
        entity_organizations=document.entity_organizations,
        entity_events=document.entity_events,
        status=document.status,
        quality_score=document.quality_score,
        created_at=document.created_at,
        markdown_content=markdown_content,
        chunk_count=len(chunks),
    )


@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    """Get chunks for a document."""
    # Verify document exists
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    if result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Count chunks
    count_result = await db.execute(
        select(func.count(DocumentChunk.id))
        .where(DocumentChunk.document_id == document_id)
    )
    total = count_result.scalar() or 0

    # Get chunks
    offset = (page - 1) * page_size
    result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
        .offset(offset)
        .limit(page_size)
    )
    chunks = result.scalars().all()

    return {
        "chunks": [DocumentChunkResponse.model_validate(c) for c in chunks],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{document_id}/markdown")
async def get_document_markdown(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Get raw markdown content of a document."""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    if document.markdown_content_path:
        try:
            import aiofiles
            async with aiofiles.open(document.markdown_content_path, "r", encoding="utf-8") as f:
                markdown_content = await f.read()
            return {"markdown": markdown_content}
        except Exception:
            pass

    return {"markdown": None}


@router.patch("/{document_id}", response_model=DocumentResponse)
async def update_document(
    document_id: str,
    data: DocumentUpdate,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Update a document."""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Update fields
    if data.title is not None:
        document.title = data.title
    if data.status is not None:
        document.status = data.status
    if data.summary is not None:
        document.summary = data.summary
    if data.tags is not None:
        document.tags = data.tags

    await db.commit()
    await db.refresh(document)

    return DocumentResponse.model_validate(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: str,
    current_user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """Delete a document, its database chunks, vector indices, and storage files."""
    result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    document = result.scalar_one_or_none()

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # 1. Delete vectors from Qdrant vector index
    try:
        from app.services.retrieval.vector_search import VectorSearch
        vector_search = VectorSearch()
        await vector_search.delete_by_document_id(document_id)
    except Exception:
        pass

    # 2. Delete document chunks from Meilisearch
    try:
        from app.services.retrieval.meilisearch_bm25 import get_meilisearch_bm25
        meili_bm25 = await get_meilisearch_bm25()
        await meili_bm25.remove_by_document_id(document_id)
    except Exception:
        pass

    # 3. Clean up physical files on disk — validate path first to prevent traversal
    import pathlib
    import shutil
    storage_path = pathlib.Path(settings.STORAGE_PATH).resolve()
    for path_str in [document.raw_content_path, document.markdown_content_path]:
        if path_str:
            try:
                file_path = pathlib.Path(path_str).resolve()
                # Ensure the file path is within the storage directory
                file_path.relative_to(storage_path)
                dir_path = file_path.parent
                if dir_path.exists() and dir_path.is_dir():
                    shutil.rmtree(dir_path)
                    break  # both are in the same folder, so delete once
            except (ValueError, OSError):
                # ValueError: path traversal attempt (relative_to fails)
                # OSError: other filesystem errors
                pass

    # 4. Delete the document from PostgreSQL (cascading will delete db document chunks)
    await db.delete(document)
    await db.commit()

    get_audit_logger().log_document_access(
        action=AuditAction.DOCUMENT_DELETE,
        doc_id=document_id,
        user_id=current_user.id,
        email=current_user.email,
        role=getattr(current_user, 'role', 'user'),
        ip_address="",
    )

    return None
