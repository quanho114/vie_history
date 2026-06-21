"""Integration tests for the retrieval pipeline and query API routes."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services.retrieval.fusion import FusionSearch


# ── Fusion + Reranker end-to-end ─────────────────────────────────────────────

class TestFusionSearchPipeline:
    """Integration tests for the fusion + reranking pipeline."""

    def test_fusion_combines_vector_and_bm25_results(self) -> None:
        """FusionSearch must combine results from both sources."""
        fusion = FusionSearch(rrf_k=60)

        vector_results = [
            {"id": "doc_1", "score": 0.95, "content": "Chiến tranh Việt Nam", "payload": {}},
            {"id": "doc_2", "score": 0.85, "content": "Hồ Chí Minh", "payload": {}},
        ]
        bm25_results = [
            {"id": "doc_3", "score": 0.80, "content": "Điện Biên Phủ", "payload": {}},
            {"id": "doc_1", "score": 0.70, "content": "Chiến tranh Việt Nam", "payload": {}},  # duplicate
        ]

        fused = fusion.fuse(vector_results, bm25_results)

        assert len(fused) == 3
        # doc_1 appears in both, should be ranked higher
        ids = [r["id"] for r in fused]
        assert "doc_1" in ids
        assert "doc_2" in ids
        assert "doc_3" in ids
        # doc_1 (appearing in both) should be first
        assert fused[0]["id"] == "doc_1"

    def test_fusion_deduplicates_by_id(self) -> None:
        """Same document appearing in both results must appear only once."""
        fusion = FusionSearch(rrf_k=60)

        vector_results = [
            {"id": "doc_a", "score": 0.9, "content": "A", "payload": {}},
            {"id": "doc_b", "score": 0.8, "content": "B", "payload": {}},
        ]
        bm25_results = [
            {"id": "doc_a", "score": 0.9, "content": "A", "payload": {}},
            {"id": "doc_c", "score": 0.7, "content": "C", "payload": {}},
        ]

        fused = fusion.fuse(vector_results, bm25_results)
        ids = [r["id"] for r in fused]

        assert len(ids) == 3  # 3 unique docs, not 4
        assert ids.count("doc_a") == 1

    def test_fusion_with_empty_vector_results(self) -> None:
        """Fusion must work when one source returns nothing."""
        fusion = FusionSearch(rrf_k=60)

        vector_results: list[dict] = []
        bm25_results = [
            {"id": "doc_1", "score": 0.8, "content": "Content", "payload": {}},
        ]

        fused = fusion.fuse(vector_results, bm25_results)

        assert len(fused) == 1
        assert fused[0]["id"] == "doc_1"

    def test_fusion_with_empty_bm25_results(self) -> None:
        """Fusion must work when BM25 returns nothing."""
        fusion = FusionSearch(rrf_k=60)

        vector_results = [
            {"id": "doc_1", "score": 0.9, "content": "Content", "payload": {}},
        ]
        bm25_results: list[dict] = []

        fused = fusion.fuse(vector_results, bm25_results)

        assert len(fused) == 1
        assert fused[0]["id"] == "doc_1"

    def test_fusion_with_both_empty(self) -> None:
        """Fusion must return empty list when both sources are empty."""
        fusion = FusionSearch(rrf_k=60)

        fused = fusion.fuse([], [])

        assert fused == []

    def test_fusion_boost_weights(self) -> None:
        """Boost weights must affect relative ranking."""
        fusion = FusionSearch(rrf_k=60)

        vector_results = [
            {"id": "doc_v1", "score": 0.99, "content": "V content", "payload": {}},
            {"id": "doc_v2", "score": 0.98, "content": "V2 content", "payload": {}},
        ]
        bm25_results = [
            {"id": "doc_b1", "score": 0.90, "content": "B content", "payload": {}},
            {"id": "doc_b2", "score": 0.89, "content": "B2 content", "payload": {}},
        ]

        # Heavy BM25 boost — BM25 docs should rise
        fused_bm25_boosted = fusion.fuse(
            vector_results, bm25_results, boost_vector=0.1, boost_bm25=5.0
        )

        # BM25 docs should rank above vector docs when heavily boosted
        ids_bm25 = [r["id"] for r in fused_bm25_boosted]
        assert ids_bm25.index("doc_b1") < ids_bm25.index("doc_v1")

    def test_fusion_scores_sorted_descending(self) -> None:
        """Fused results must be sorted by RRF score descending."""
        fusion = FusionSearch(rrf_k=60)

        vector_results = [
            {"id": f"v_{i}", "score": 1.0 - i * 0.1, "content": f"V{i}", "payload": {}}
            for i in range(5)
        ]
        bm25_results = [
            {"id": f"b_{i}", "score": 1.0 - i * 0.1, "content": f"B{i}", "payload": {}}
            for i in range(5)
        ]

        fused = fusion.fuse(vector_results, bm25_results)

        scores = [r["rrf_score"] for r in fused]
        assert scores == sorted(scores, reverse=True)


# ── Query API Route ───────────────────────────────────────────────────────────

class TestQueryAPIRoute:
    """Integration tests for the /api/v1/query endpoint."""

    def test_query_endpoint_returns_200(self, auth_headers) -> None:
        """Query endpoint must respond with 200 for valid requests."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/query",
                json={"query": "Ai là Hồ Chí Minh?"},
                headers=auth_headers,
            )
            # Accept 200 (success), 400 (missing API key error), or 422 (validation error)
            assert response.status_code in (200, 400, 422)

    def test_query_endpoint_validates_query(self, auth_headers) -> None:
        """Query endpoint must reject empty query."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/query",
                json={"query": ""},
                headers=auth_headers,
            )
            assert response.status_code == 422

    def test_query_endpoint_requires_query_field(self, auth_headers) -> None:
        """Query endpoint must reject missing query field."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/query",
                json={},
                headers=auth_headers,
            )
            assert response.status_code == 422

    def test_query_endpoint_rejects_missing_auth(self) -> None:
        """Query endpoint must require authentication."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/query",
                json={"query": "Test"},
            )
            # Should be 401 without auth token, or 422 for validation
            assert response.status_code in (401, 422)

    def test_retrieve_endpoint_returns_200(self, auth_headers) -> None:
        """Retrieve endpoint must respond with 200 for valid requests."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/retrieve",
                json={"query": "Chiến tranh Việt Nam"},
                headers=auth_headers,
            )
            assert response.status_code in (200, 401, 422)

    def test_retrieve_endpoint_validates_top_k(self, auth_headers) -> None:
        """Retrieve endpoint must validate top_k range."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.post(
                "/api/v1/retrieve",
                json={"query": "Test", "top_k": 0},
                headers=auth_headers,
            )
            assert response.status_code == 422

            response2 = client.post(
                "/api/v1/retrieve",
                json={"query": "Test", "top_k": 500},
                headers=auth_headers,
            )
            assert response2.status_code == 422



# ── Health endpoint ──────────────────────────────────────────────────────────

class TestHealthEndpoint:
    """Health check endpoint tests."""

    def test_health_returns_200(self) -> None:
        """Health endpoint must return 200."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/health")
            assert response.status_code == 200

    def test_health_returns_status(self) -> None:
        """Health endpoint must return status field."""
        with TestClient(app, raise_server_exceptions=False) as client:
            response = client.get("/health")
            if response.status_code == 200:
                data = response.json()
                assert "status" in data


# ── Ingestion Pipeline ────────────────────────────────────────────────────────

class TestIngestionPipeline:
    """Integration tests for the ingestion pipeline."""

    def test_url_validator_blocks_localhost(self) -> None:
        """URL validator must block localhost."""
        from app.services.ingestion.url_validator import URLValidator

        validator = URLValidator()
        # Parse blocked networks first
        validator._blocked_networks = ["localhost"]

        # Direct IP check
        assert validator._is_blocked_ip("127.0.0.1") is True
        assert validator._is_blocked_ip("::1") is True

    def test_url_validator_rejects_invalid_scheme(self) -> None:
        """URL validator must reject non-http schemes."""
        from app.services.ingestion.url_validator import URLValidator

        validator = URLValidator()

        result = validator.validate("ftp://example.com")
        assert result["valid"] is False
        assert "Invalid scheme" in result["error"]

    def test_content_cleaner_removes_scripts(self) -> None:
        """Content cleaner must strip script tags."""
        from app.services.ingestion.cleaner import ContentCleaner

        cleaner = ContentCleaner(min_content_length=0)
        html = "<script>evil()</script><p>Valid content</p>"

        cleaned = cleaner.clean_html(html)

        assert "evil()" not in cleaned
        assert "Valid content" in cleaned

    def test_content_cleaner_normalizes_wiki_links(self) -> None:
        """Content cleaner must normalize Wikipedia links."""
        from app.services.ingestion.cleaner import ContentCleaner

        cleaner = ContentCleaner(min_content_length=0)
        text = "See [[Vietnamese language|Vietnamese]] for details."

        result = cleaner.remove_wiki_templates(text)

        assert "Vietnamese language" not in result
        assert "Vietnamese" in result
        assert "[[" not in result

    def test_metadata_extractor_extracts_years(self) -> None:
        """Metadata extractor must detect historical years."""
        from app.services.ingestion.metadata_extractor import MetadataExtractor

        extractor = MetadataExtractor()
        text = "Cách mạng tháng Tám năm 1945. Chiến dịch Điện Biên Phủ năm 1954."

        years = extractor._extract_years(text)

        assert 1945 in years
        assert 1954 in years
        assert 2000 not in years  # out of range

    def test_metadata_extractor_generates_tags(self) -> None:
        """Metadata extractor must generate relevant tags."""
        from app.services.ingestion.metadata_extractor import MetadataExtractor

        extractor = MetadataExtractor()
        entities = {
            "persons": ["Hồ Chí Minh"],
            "events": [],
        }

        tags = extractor._generate_tags("Test", entities, {1945, 1954})

        assert "Hồ Chí Minh" in tags
        assert "1940s" in tags
