"""Unit tests for RRF fusion logic."""

import pytest

from app.services.retrieval.fusion import FusionSearch


class TestFusionSearch:
    """Tests for Reciprocal Rank Fusion."""

    @pytest.fixture
    def fusion(self) -> FusionSearch:
        return FusionSearch(rrf_k=60)

    def test_fuse_empty_both(self, fusion: FusionSearch) -> None:
        result = fusion.fuse(vector_results=[], bm25_results=[])
        assert result == []

    def test_fuse_vector_only(self, fusion: FusionSearch) -> None:
        vector = [
            {"id": "1", "score": 0.9, "payload": {"content": "doc1"}},
            {"id": "2", "score": 0.8, "payload": {"content": "doc2"}},
        ]
        result = fusion.fuse(vector_results=vector, bm25_results=[])
        assert len(result) == 2
        assert result[0]["id"] == "1"
        assert result[1]["id"] == "2"

    def test_fuse_bm25_only(self, fusion: FusionSearch) -> None:
        bm25 = [
            {"id": "A", "score": 1.5, "payload": {"content": "docA"}},
            {"id": "B", "score": 1.0, "payload": {"content": "docB"}},
        ]
        result = fusion.fuse(vector_results=[], bm25_results=bm25)
        assert len(result) == 2
        assert result[0]["id"] == "A"

    def test_fuse_combines_ranks(self, fusion: FusionSearch) -> None:
        """Doc ranked 1st in vector + 2nd in BM25 should rank high via RRF."""
        vector = [
            {"id": "vec_only", "score": 0.9, "payload": {}},
            {"id": "shared", "score": 0.8, "payload": {}},
        ]
        bm25 = [
            {"id": "bm25_only", "score": 2.0, "payload": {}},
            {"id": "shared", "score": 1.5, "payload": {}},
        ]
        result = fusion.fuse(vector_results=vector, bm25_results=bm25)
        ids = [r["id"] for r in result]
        # shared doc should be first (rank 2 in both lists)
        # vec_only should be second (rank 1 in vector only)
        # bm25_only should be third (rank 1 in bm25 only)
        assert ids == ["shared", "vec_only", "bm25_only"]

    def test_fuse_deduplicates_by_id(self, fusion: FusionSearch) -> None:
        vector = [
            {"id": "same", "score": 0.9, "payload": {}},
        ]
        bm25 = [
            {"id": "same", "score": 1.5, "payload": {}},
        ]
        result = fusion.fuse(vector_results=vector, bm25_results=bm25)
        assert len(result) == 1
        assert result[0]["id"] == "same"

    def test_fuse_respects_top_k(self, fusion: FusionSearch) -> None:
        vector = [
            {"id": f"v{i}", "score": 0.9 - i * 0.05, "payload": {}}
            for i in range(10)
        ]
        bm25 = [
            {"id": f"b{i}", "score": 2.0 - i * 0.1, "payload": {}}
            for i in range(10)
        ]
        result = fusion.fuse(vector_results=vector, bm25_results=bm25, top_k=3)
        assert len(result) == 3

    def test_fuse_boost_vector(self, fusion: FusionSearch) -> None:
        """High vector boost should favor semantic results."""
        vector = [
            {"id": "vec_doc", "score": 0.9, "payload": {}},
        ]
        bm25 = [
            {"id": "bm25_doc", "score": 2.0, "payload": {}},
        ]
        boosted = fusion.fuse(
            vector_results=vector,
            bm25_results=bm25,
            boost_vector=10.0,
            boost_bm25=0.1,
        )
        assert boosted[0]["id"] == "vec_doc"

    def test_fuse_boost_bm25(self, fusion: FusionSearch) -> None:
        """High BM25 boost should favor keyword results."""
        vector = [
            {"id": "vec_doc", "score": 0.9, "payload": {}},
        ]
        bm25 = [
            {"id": "bm25_doc", "score": 2.0, "payload": {}},
        ]
        boosted = fusion.fuse(
            vector_results=vector,
            bm25_results=bm25,
            boost_vector=0.1,
            boost_bm25=10.0,
        )
        assert boosted[0]["id"] == "bm25_doc"

    def test_fuse_preserves_payload(self, fusion: FusionSearch) -> None:
        vector = [
            {"id": "1", "score": 0.9, "payload": {"content": "text", "year": 1945}},
        ]
        result = fusion.fuse(vector_results=vector, bm25_results=[])
        assert result[0]["payload"]["content"] == "text"
        assert result[0]["payload"]["year"] == 1945

    def test_fuse_sets_rrf_score(self, fusion: FusionSearch) -> None:
        vector = [{"id": "1", "score": 0.9, "payload": {}}]
        bm25 = [{"id": "1", "score": 1.5, "payload": {}}]
        result = fusion.fuse(vector_results=vector, bm25_results=bm25)
        assert "rrf_score" in result[0]
        assert result[0]["rrf_score"] > 0
