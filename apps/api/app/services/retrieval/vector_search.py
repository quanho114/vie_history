"""Vector search service using Qdrant."""

from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.http import models

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("vector_search")


class VectorSearch:
    """
    Vector search service using Qdrant.
    """

    def __init__(
        self,
        url: str | None = None,
        collection_name: str | None = None,
        vector_size: int | None = None,
    ):
        self.url = url or settings.QDRANT_URL
        self.collection_name = collection_name or settings.QDRANT_COLLECTION
        self.vector_size = vector_size or settings.QDRANT_VECTOR_SIZE
        self._client: QdrantClient | None = None

    async def connect(self) -> None:
        """Connect to Qdrant and ensure collection exists."""
        if self._client is None:
            self._client = QdrantClient(url=self.url)
            await self._ensure_collection()

    def _ensure_collection_sync(self) -> None:
        """Sync version of collection check."""
        if self._client is None:
            return

        try:
            collections = self._client.get_collections().collections
            collection_names = [c.name for c in collections]

            if self.collection_name not in collection_names:
                self._client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=models.VectorParams(
                        size=self.vector_size,
                        distance=models.Distance.COSINE,
                    ),
                )
                logger.info("collection_created", collection=self.collection_name)
        except Exception as e:
            logger.error("collection_check_error", error=str(e))

    async def _ensure_collection(self) -> None:
        """Ensure collection exists."""
        import asyncio
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._ensure_collection_sync)

    @property
    def client(self) -> QdrantClient:
        """Get Qdrant client."""
        if self._client is None:
            self._client = QdrantClient(url=self.url)
        return self._client

    async def search(
        self,
        query_vector: list[float],
        top_k: int = 10,
        filters: dict | None = None,
        score_threshold: float | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar vectors.

        Args:
            query_vector: Query embedding vector
            top_k: Number of results to return
            filters: Optional metadata filters
            score_threshold: Minimum similarity score

        Returns:
            List of search results with payload
        """
        try:
            await self.connect()
            # Build filter
            qdrant_filter = None
            if filters:
                must_conditions = []
                if "year_from" in filters or "year_to" in filters:
                    year_from = filters.get("year_from", 1945)
                    year_to = filters.get("year_to", 1975)
                    must_conditions.append(
                        models.FieldCondition(
                            key="year",
                            range=models.Range(
                                gte=year_from,
                                lte=year_to,
                                            ),
                        )
                    )
                if "document_id" in filters:
                    must_conditions.append(
                        models.FieldCondition(
                            key="document_id",
                            match=models.MatchValue(value=filters["document_id"]),
                        )
                    )
                if must_conditions:
                    qdrant_filter = models.Filter(must=must_conditions)

            # qdrant-client ≥1.7 uses query_points(); fall back to search() for older versions or servers
            try:
                result = self.client.query_points(
                    collection_name=self.collection_name,
                    query=query_vector,
                    limit=top_k,
                    query_filter=qdrant_filter,
                    score_threshold=score_threshold,
                    with_payload=True,
                    with_vectors=False,
                )
                results = result.points
            except Exception as e:
                # Fallback to REST API search if query_points is not supported or client version is incompatible
                try:
                    import httpx
                    import json
                    filter_dict = None
                    if qdrant_filter:
                        if hasattr(qdrant_filter, "model_dump"):
                            filter_dict = qdrant_filter.model_dump()
                        elif hasattr(qdrant_filter, "dict"):
                            filter_dict = qdrant_filter.dict()
                        else:
                            filter_dict = json.loads(qdrant_filter.json())
                    
                    search_payload = {
                        "vector": query_vector,
                        "limit": top_k,
                        "filter": filter_dict,
                        "with_payload": True,
                        "with_vector": False
                    }
                    if score_threshold is not None:
                        search_payload["score_threshold"] = score_threshold
                    
                    async with httpx.AsyncClient(timeout=10.0) as http_client:
                        resp = await http_client.post(
                            f"{self.url.rstrip('/')}/collections/{self.collection_name}/points/search",
                            json=search_payload
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            results = []
                            class Hit:
                                def __init__(self, id, score, payload):
                                    self.id = id
                                    self.score = score
                                    self.payload = payload
                            for r in data.get("result", []):
                                results.append(Hit(
                                    id=r.get("id"),
                                    score=r.get("score"),
                                    payload=r.get("payload")
                                ))
                        else:
                            raise Exception(f"Qdrant REST search failed: {resp.text}")
                except Exception as rest_exc:
                    logger.error("vector_search_rest_fallback_error", error=str(rest_exc))
                    return []



            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload,
                }
                for hit in results
            ]

        except Exception as e:
            logger.error("vector_search_error", error=str(e))
            return []

    async def upsert(
        self,
        vectors: list[tuple[str, list[float]]],
        payloads: list[dict],
    ) -> bool:
        """
        Insert or update vectors.

        Args:
            vectors: List of (id, vector) tuples
            payloads: List of payload dicts

        Returns:
            True if successful
        """
        try:
            await self.connect()
            points = [
                models.PointStruct(
                    id=vid,
                    vector=vec,
                    payload=payload,
                )
                for (vid, vec), payload in zip(vectors, payloads)
            ]

            self.client.upsert(
                collection_name=self.collection_name,
                points=points,
            )
            return True

        except Exception as e:
            logger.error("vector_upsert_error", error=str(e))
            return False

    async def delete(self, point_ids: list[str]) -> bool:
        """Delete points by ID."""
        try:
            await self.connect()
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=point_ids),
            )
            return True
        except Exception as e:
            logger.error("vector_delete_error", error=str(e))
            return False

    async def delete_by_document_id(self, document_id: str) -> bool:
        """Delete points by document_id filter."""
        try:
            await self.connect()
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="document_id",
                                match=models.MatchValue(value=document_id),
                            )
                        ]
                    )
                ),
            )
            return True
        except Exception as e:
            logger.error("vector_delete_by_document_id_error", error=str(e))
            return False
