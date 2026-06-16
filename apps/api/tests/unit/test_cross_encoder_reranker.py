"""Unit tests for cross-encoder reranker."""

import pytest

from app.services.retrieval.cross_encoder_reranker import CrossEncoderReranker


class TestCrossEncoderReranker:
    """Tests for cross-encoder reranking logic."""

    def test_rerank_orders_by_cross_encoder_score(self) -> None:
        reranker = CrossEncoderReranker(
            model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
            blend_weight=0.7,
        )
        reranker._available = True  # mock available
        reranker._model = lambda pairs: [0.95, 0.30]  # mock model scoring

        candidates = [
            {
                "id": "A",
                "content": "Điện Biên Phủ là trận đánh lớn năm 1954",
                "score": 0.5,  # first-stage score
                "rrf_score": 0.5,
                "payload": {},
            },
            {
                "id": "B",
                "content": "Chiến tranh Việt Nam kéo dài từ 1955 đến 1975",
                "score": 0.9,  # higher first-stage score
                "rrf_score": 0.9,
                "payload": {},
            },
        ]

        result = reranker.rerank(
            query="Trận Điện Biên Phủ năm 1954",
            candidates=candidates,
            top_k=2,
        )

        # Doc A should rank first — cross-encoder gives it higher score
        assert result[0]["id"] == "A"
        assert result[1]["id"] == "B"
        assert "cross_encoder_score" in result[0]
        assert "rerank_score" in result[0]
        assert 0 <= result[0]["cross_encoder_score"] <= 1

    def test_rerank_respects_top_k(self) -> None:
        reranker = CrossEncoderReranker()
        reranker._available = True
        reranker._model = lambda pairs: [0.5] * 5

        candidates = [
            {"id": str(i), "content": f"doc {i}", "score": 0.1 * i, "rrf_score": 0.1 * i, "payload": {}}
            for i in range(1, 6)
        ]

        result = reranker.rerank(
            query="test query",
            candidates=candidates,
            top_k=3,
        )
        assert len(result) == 3

    def test_rerank_empty_returns_empty(self) -> None:
        reranker = CrossEncoderReranker()
        reranker._available = True
        result = reranker.rerank(query="test", candidates=[], top_k=5)
        assert result == []

    def test_rerank_falls_back_when_unavailable(self) -> None:
        reranker = CrossEncoderReranker()
        reranker._available = False

        candidates = [
            {"id": "1", "content": "doc1", "score": 0.9, "rrf_score": 0.9, "payload": {}},
            {"id": "2", "content": "doc2", "score": 0.1, "rrf_score": 0.1, "payload": {}},
        ]

        result = reranker.rerank(
            query="test",
            candidates=candidates,
            top_k=2,
        )
        # Should return candidates sorted by existing score (no cross-encoder)
        assert len(result) == 2
        assert "cross_encoder_score" in result[0]

    def test_rerank_preserves_all_fields(self) -> None:
        reranker = CrossEncoderReranker()
        reranker._available = True
        reranker._model = lambda pairs: [0.8]

        candidates = [
            {
                "id": "1",
                "content": "test content",
                "score": 0.5,
                "rrf_score": 0.5,
                "payload": {"document_title": "Test Doc", "year": 1945},
                "vector_score": 0.4,
                "bm25_score": 0.6,
            },
        ]

        result = reranker.rerank(query="test", candidates=candidates, top_k=1)

        assert result[0]["id"] == "1"
        assert result[0]["payload"]["document_title"] == "Test Doc"
        assert result[0]["payload"]["year"] == 1945
        assert result[0]["vector_score"] == 0.4
        assert result[0]["bm25_score"] == 0.6

    def test_is_available_reflects_model_state(self) -> None:
        reranker = CrossEncoderReranker()
        assert reranker.is_available == (reranker._model is not None)
