"""Application service for durable document ingestion."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.document import Document, DocumentChunk
from app.models.ingest_job import IngestJob
from app.services.ingestion.pipeline import IngestionPipeline
from app.services.ingestion.file_extractor import FileExtractor
from app.services.retrieval.embedder import Embedder
from app.services.retrieval.vector_search import VectorSearch

logger = get_logger("ingest_service")


class IngestService:
    """Coordinates URL ingestion, persistence, chunking, and best-effort indexing."""

    def __init__(
        self,
        pipeline: IngestionPipeline | None = None,
        embedder: Embedder | None = None,
        vector_search: VectorSearch | None = None,
        file_extractor: FileExtractor | None = None,
    ) -> None:
        self.pipeline = pipeline or IngestionPipeline()
        self.embedder = embedder or Embedder()
        self.vector_search = vector_search or VectorSearch()
        self.file_extractor = file_extractor or FileExtractor()

    async def ingest_url(
        self,
        db: AsyncSession,
        url: str,
        user_id: str,
        tags: list[str] | None = None,
    ) -> IngestJob:
        """Ingest a URL immediately and return the completed/failed job."""
        job = IngestJob(
            source_input=url,
            source_type="url",
            status="running",
            stage="url_validation",
            started_at=datetime.now(timezone.utc),
        )
        job.add_log("Ingestion started")
        db.add(job)
        await db.commit()
        await db.refresh(job)

        try:
            result = await self.pipeline.process_url(url=url, tags=tags)
            if not result["success"]:
                await self._mark_failed(db, job, result["stage"], result["error"])
                return job

            job.stage = "persistence"
            job.add_log("Content extracted and cleaned")
            document = await self._persist_document(db, result, user_id)
            chunks = await self._persist_chunks(db, document, result["markdown"])

            job.stage = "indexing"
            indexed = await self._index_chunks(document, chunks, db)
            job.add_log(
                f"Indexed {len(chunks)} chunks (vector={indexed['vector']}, es_bm25={indexed['bm25']})",
                "info",
            )

            job.status = "done"
            job.stage = "done"
            job.document_id = document.id
            job.finished_at = datetime.now(timezone.utc)
            job.add_log("Ingestion completed")
            
            # Auto-approve document on successful ingestion
            document.status = "approved"
            
            await db.commit()
            await db.refresh(job)
            return job
        except Exception as exc:
            logger.exception("ingest_url_failed", error=str(exc), url=url)
            await self._mark_failed(db, job, "unexpected_error", str(exc))
            return job

    async def retry_job(self, db: AsyncSession, job: IngestJob, user_id: str) -> IngestJob:
        """Retry an existing URL job."""
        job.status = "queued"
        job.error_message = None
        job.stage = "queued"
        job.add_log("Retry queued")
        await db.commit()
        return await self.ingest_url(db=db, url=job.source_input, user_id=user_id)

    async def ingest_file(
        self,
        db: AsyncSession,
        file_path: Path,
        filename: str,
        user_id: str,
        content_type: str | None = None,
        tags: list[str] | None = None,
    ) -> IngestJob:
        """Ingest a local file immediately."""
        job = IngestJob(
            source_input=filename,
            source_type="file",
            status="running",
            stage="extraction",
            started_at=datetime.now(timezone.utc),
        )
        job.add_log("File ingestion started")
        db.add(job)
        await db.commit()
        await db.refresh(job)

        try:
            text = await self.file_extractor.extract(file_path=file_path, content_type=content_type)
            markdown = self.pipeline.cleaner.clean_markdown(text)
            markdown = await self.pipeline.restructure_markdown_with_llm(filename, markdown)
            is_valid, error = self.pipeline.cleaner.validate_content(markdown)
            if not is_valid:
                await self._mark_failed(db, job, "quality_validation", error)
                return job

            metadata = self.pipeline.metadata_extractor.extract(
                markdown=markdown,
                title=filename,
                source_url=None,
            )
            if tags:
                metadata["tags"] = list(set(metadata.get("tags", []) + tags))

            result = {
                "url": f"file://{filename}",
                "title": filename,
                "markdown": markdown,
                "html": "",
                "metadata": {**metadata, "source_type": file_path.suffix.lower().lstrip(".") or "file"},
            }
            document = await self._persist_document(db, result, user_id)
            chunks = await self._persist_chunks(db, document, markdown)
            indexed = await self._index_chunks(document, chunks, db)

            job.status = "done"
            job.stage = "done"
            job.document_id = document.id
            job.finished_at = datetime.now(timezone.utc)
            
            # Auto-approve document on successful ingestion
            document.status = "approved"
            
            job.add_log(
                f"File ingestion done: {len(chunks)} chunks "
                f"(vector={indexed['vector']}, es_bm25={indexed['bm25']})"
            )
            await db.commit()
            await db.refresh(job)
            return job
        except Exception as exc:
            logger.exception("ingest_file_failed", error=str(exc), filename=filename)
            await self._mark_failed(db, job, "file_extraction", str(exc))
            return job

    async def reindex_document(self, db: AsyncSession, document: Document) -> bool:
        """Reindex existing chunks for a document (both vector + ES BM25)."""
        result = await db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.document_id == document.id)
            .order_by(DocumentChunk.chunk_index)
        )
        chunks = list(result.scalars().all())
        indexed = await self._index_chunks(document, chunks, db)
        return indexed["vector"] or indexed["bm25"]

    async def _persist_document(
        self,
        db: AsyncSession,
        result: dict[str, Any],
        user_id: str,
    ) -> Document:
        """Create or update the document row and content files."""
        metadata = result.get("metadata", {})
        content_paths = self._write_content_files(
            document_slug=str(uuid4()),
            html=result.get("html", ""),
            markdown=result["markdown"],
        )

        canonical_url = result["url"] if not result["url"].startswith("file://") else None
        existing = None
        if canonical_url:
            existing_result = await db.execute(
                select(Document).where(Document.canonical_url == canonical_url)
            )
            existing = existing_result.scalar_one_or_none()

        if existing:
            document = existing
            document.title = result.get("title") or metadata.get("title") or document.title
            document.summary = metadata.get("summary")
            document.tags = metadata.get("tags")
            document.detected_years = metadata.get("detected_years")
            document.entity_persons = metadata.get("entity_persons")
            document.entity_places = metadata.get("entity_places")
            document.entity_organizations = metadata.get("entity_organizations")
            document.entity_events = metadata.get("entity_events")
            document.raw_content_path = str(content_paths["html"])
            document.markdown_content_path = str(content_paths["markdown"])
            document.metadata_json = metadata
            document.period = metadata.get("period")
            document.year = metadata.get("year")
            document.dynasty = metadata.get("dynasty")
            document.geographical_region = metadata.get("geographical_region")
            document.event_type = metadata.get("event_type")
            document.confidence = metadata.get("confidence", 0.0)
            document.historical_metadata = metadata.get("historical_metadata")
        else:
            document = Document(
                title=result.get("title") or metadata.get("title") or result["url"],
                source_url=result["url"],
                canonical_url=canonical_url,
                source_domain=metadata.get("source_domain"),
                source_type=metadata.get("source_type", "unknown"),
                author=metadata.get("author"),
                language="vi",
                summary=metadata.get("summary"),
                tags=metadata.get("tags"),
                detected_years=metadata.get("detected_years"),
                entity_persons=metadata.get("entity_persons"),
                entity_places=metadata.get("entity_places"),
                entity_organizations=metadata.get("entity_organizations"),
                entity_events=metadata.get("entity_events"),
                status="pending",
                quality_score=self._quality_score(result["markdown"], metadata),
                raw_content_path=str(content_paths["html"]),
                markdown_content_path=str(content_paths["markdown"]),
                metadata_json=metadata,
                period=metadata.get("period"),
                year=metadata.get("year"),
                dynasty=metadata.get("dynasty"),
                geographical_region=metadata.get("geographical_region"),
                event_type=metadata.get("event_type"),
                confidence=metadata.get("confidence", 0.0),
                historical_metadata=metadata.get("historical_metadata"),
                created_by=user_id,
            )
            db.add(document)

        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            if canonical_url is None:
                raise
            existing_result = await db.execute(
                select(Document).where(Document.canonical_url == canonical_url)
            )
            document = existing_result.scalar_one()

        await db.refresh(document)
        return document

    async def _persist_chunks(
        self,
        db: AsyncSession,
        document: Document,
        markdown: str,
    ) -> list[DocumentChunk]:
        """Replace chunks for a document."""
        await db.execute(
            delete(DocumentChunk).where(DocumentChunk.document_id == document.id)
        )
        await db.flush()

        chunk_payloads = self.pipeline.chunk_text(markdown)
        chunks: list[DocumentChunk] = []
        for payload in chunk_payloads:
            content = payload["content"].strip()
            if not content:
                continue
            chunk = DocumentChunk(
                document_id=document.id,
                chunk_index=payload["index"],
                section_title=payload.get("title"),
                content=content,
                token_count=len(content.split()),
                chunk_metadata={"source_type": document.source_type},
            )
            db.add(chunk)
            chunks.append(chunk)

        await db.commit()
        for chunk in chunks:
            await db.refresh(chunk)
        return chunks

    async def _index_chunks(
        self,
        document: Document,
        chunks: list[DocumentChunk],
        db: AsyncSession | None = None,
    ) -> dict[str, bool]:
        """
        Best-effort dual-indexing: vector (Qdrant) + lexical (Elasticsearch).

        Failures are non-fatal — the chunks are already in PostgreSQL and will
        be indexed on next startup or manual reindex.
        """
        indexed = {"vector": False, "bm25": False}

        if not chunks:
            return indexed

        try:
            texts = [chunk.content for chunk in chunks]
            embeddings = await self.embedder.embed_async(texts)
            vectors = [
                (chunk.id, embeddings[index].tolist())
                for index, chunk in enumerate(chunks)
            ]
            payloads = [
                {
                    "document_id": document.id,
                    "document_title": document.title,
                    "source_url": document.source_url,
                    "section_title": chunk.section_title,
                    "content": chunk.content,
                    "year": (document.detected_years or [None])[0],
                    "dynasty": document.dynasty,
                    "geographical_region": document.geographical_region,
                }
                for chunk in chunks
            ]
            indexed["vector"] = await self.vector_search.upsert(vectors=vectors, payloads=payloads)
        except Exception as exc:
            logger.warning("vector_indexing_failed", error=str(exc), document_id=document.id)

        # Meilisearch BM25 — bulk index all chunks
        try:
            from app.services.retrieval.meilisearch_bm25 import get_meilisearch_bm25
            meili_bm25 = await get_meilisearch_bm25()
            meili_chunks = [
                {
                    "id":         chunk.id,
                    "document_id": document.id,
                    "document_title": document.title,
                    "section_title": chunk.section_title,
                    "content":    chunk.content,
                    "year":       (document.detected_years or [None])[0],
                    "source_url": document.source_url,
                    "quality_score": document.quality_score,
                    "token_count": chunk.token_count,
                    "dynasty": document.dynasty,
                    "geographical_region": document.geographical_region,
                }
                for chunk in chunks
            ]
            meili_indexed = await meili_bm25.index_chunks(meili_chunks)
            indexed["bm25"] = meili_indexed > 0
            logger.info("meili_chunk_indexed", document_id=document.id, chunks=meili_indexed)
        except Exception as exc:
            logger.warning("meili_bm25_indexing_failed", error=str(exc), document_id=document.id)

        return indexed

    def _write_content_files(self, document_slug: str, html: str, markdown: str) -> dict[str, Path]:
        base_path = settings.STORAGE_PATH / "documents" / document_slug
        base_path.mkdir(parents=True, exist_ok=True)

        html_path = base_path / "raw.html"
        markdown_path = base_path / "content.md"
        html_path.write_text(html, encoding="utf-8")
        markdown_path.write_text(markdown, encoding="utf-8")
        return {"html": html_path, "markdown": markdown_path}

    def _quality_score(self, markdown: str, metadata: dict[str, Any]) -> float:
        score = 0.45
        if len(markdown) >= 2_000:
            score += 0.2
        if metadata.get("detected_years"):
            score += 0.15
        if metadata.get("entity_persons") or metadata.get("entity_events"):
            score += 0.1
        if metadata.get("source_domain"):
            score += 0.1
        return min(score, 1.0)

    async def _mark_failed(
        self,
        db: AsyncSession,
        job: IngestJob,
        stage: str,
        error: str,
    ) -> None:
        job.status = "failed"
        job.stage = stage
        job.error_message = error
        job.finished_at = datetime.now(timezone.utc)
        job.add_log(error, "error")
        await db.commit()
        await db.refresh(job)
