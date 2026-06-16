"""Unit tests for retrieval evaluation metrics and logic."""

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../..")))

import pytest
import math

from scripts.eval_retrieval import (
    compute_dcg,
    compute_ndcg,
    relevance_labels,
    evaluate_single,
    aggregate_report,
    GoldenQuestion,
    RetrievalResult,
)


class TestDCG:
    def test_dcg_empty(self) -> None:
        assert compute_dcg([]) == 0.0

    def test_dcg_single_relevant(self) -> None:
        assert compute_dcg([1]) == 1.0

    def test_dcg_discounts_lower_positions(self) -> None:
        # Position 1: 1/log2(2) = 1.0
        # Position 3: 1/log2(4) = 0.5
        dcg_full = compute_dcg([1, 0, 1])
        dcg_k3 = compute_dcg([1, 0, 1], k=3)
        assert dcg_k3 == pytest.approx(dcg_full)

    def test_dcg_respects_k(self) -> None:
        dcg_full = compute_dcg([1, 1, 1, 1, 1])
        dcg_k3 = compute_dcg([1, 1, 1, 1, 1], k=3)
        assert dcg_k3 < dcg_full


class TestNDCG:
    def test_ndcg_empty(self) -> None:
        assert compute_ndcg([]) == 0.0

    def test_ndcg_perfect_order(self) -> None:
        labels = [1, 1, 0, 1, 0]
        assert compute_ndcg(labels) == 1.0

    def test_ndcg_partial_order(self) -> None:
        # Worst order: relevant docs at bottom
        worst = [0, 0, 1, 0, 1]
        # Best order: relevant docs at top
        best = [1, 1, 0, 0, 0]
        ndcg_worst = compute_ndcg(worst)
        ndcg_best = compute_ndcg(best)
        assert 0 < ndcg_worst < ndcg_best <= 1.0


class TestRelevanceLabels:
    def test_relevant_when_content_matches(self) -> None:
        chunks = [
            {"content": "Cách mạng tháng Tám 1945", "document_title": "History", "section_title": ""},
        ]
        labels = relevance_labels(chunks, {"cách mạng", "tháng tám"})
        assert labels == [1]

    def test_not_relevant_when_no_match(self) -> None:
        chunks = [
            {"content": "Chiến tranh thế giới thứ hai", "document_title": "WW2", "section_title": ""},
        ]
        labels = relevance_labels(chunks, {"kinh tế", "tài chính"})
        assert labels == [0]

    def test_relevant_in_title(self) -> None:
        chunks = [
            {"content": "A long document", "document_title": "Điện Biên Phủ 1954", "section_title": ""},
        ]
        labels = relevance_labels(chunks, {"điện biên phủ"})
        assert labels == [1]

    def test_relevant_in_section(self) -> None:
        chunks = [
            {"content": "Some content", "document_title": "Doc", "section_title": "Chiến dịch Hồ Chí Minh"},
        ]
        labels = relevance_labels(chunks, {"hồ chí minh"})
        assert labels == [1]

    def test_case_insensitive(self) -> None:
        chunks = [
            {"content": "ĐIỆN BIÊN PHỦ", "document_title": "", "section_title": ""},
        ]
        labels = relevance_labels(chunks, {"điện biên phủ"})
        assert labels == [1]


class TestEvaluateSingle:
    def test_mrr_hit_at_position_1(self) -> None:
        q = GoldenQuestion(
            question="Test?",
            expected_source_contains=["keyword"],
        )
        chunks = [
            {"content": "keyword here", "document_title": "", "section_title": ""},
            {"content": "other", "document_title": "", "section_title": ""},
        ]
        result = evaluate_single(q, chunks, elapsed_ms=50, k_values=[1, 3, 5])
        assert result.mrr == 1.0
        assert result.hits == [1]

    def test_mrr_hit_at_position_3(self) -> None:
        q = GoldenQuestion(question="Test?", expected_source_contains=["found"])
        chunks = [
            {"content": "no", "document_title": "", "section_title": ""},
            {"content": "no", "document_title": "", "section_title": ""},
            {"content": "found it here", "document_title": "", "section_title": ""},
        ]
        result = evaluate_single(q, chunks, elapsed_ms=50, k_values=[1, 3, 5])
        assert result.mrr == pytest.approx(1.0 / 3.0)
        assert result.hits == [3]

    def test_mrr_zero_when_no_hit(self) -> None:
        q = GoldenQuestion(question="Test?", expected_source_contains=["xyz123"])
        chunks = [
            {"content": "completely unrelated", "document_title": "", "section_title": ""},
        ]
        result = evaluate_single(q, chunks, elapsed_ms=50, k_values=[1, 3, 5])
        assert result.mrr == 0.0
        assert result.hits == []

    def test_multiple_hits(self) -> None:
        q = GoldenQuestion(question="Test?", expected_source_contains=["key"])
        chunks = [
            {"content": "key content", "document_title": "", "section_title": ""},
            {"content": "other", "document_title": "", "section_title": ""},
            {"content": "keyword again", "document_title": "", "section_title": ""},
        ]
        result = evaluate_single(q, chunks, elapsed_ms=50, k_values=[1, 3, 5])
        assert result.hits == [1, 3]
        assert result.mrr == 1.0  # MRR uses first hit only


class TestAggregateReport:
    def test_hit_rate_at_k(self) -> None:
        results = [
            RetrievalResult(question="q1", chunks=[], elapsed_ms=10, hits=[1]),
            RetrievalResult(question="q2", chunks=[], elapsed_ms=10, hits=[]),  # MISS
            RetrievalResult(question="q3", chunks=[], elapsed_ms=10, hits=[3]),
            RetrievalResult(question="q4", chunks=[], elapsed_ms=10, hits=[]),  # MISS
        ]
        report = aggregate_report(results, k_values=[1, 3, 5], timestamp="2026-01-01T00:00:00")

        assert report.total == 4
        assert report.hit_rate_at_1 == 0.25   # 1/4 hits at k=1
        assert report.hit_rate_at_3 == 0.5   # 2/4 hits at k=3
        assert report.hit_rate_at_5 == 0.5   # 2/4 hits at k=5

    def test_mean_mrr(self) -> None:
        results = [
            RetrievalResult(question="q1", chunks=[], elapsed_ms=10, mrr=1.0, hits=[1]),
            RetrievalResult(question="q2", chunks=[], elapsed_ms=10, mrr=0.5, hits=[2]),
            RetrievalResult(question="q3", chunks=[], elapsed_ms=10, mrr=0.0, hits=[]),
        ]
        report = aggregate_report(results, k_values=[1, 3], timestamp="2026-01-01T00:00:00")
        assert report.mean_mrr == pytest.approx((1.0 + 0.5 + 0.0) / 3)

    def test_avg_latency(self) -> None:
        results = [
            RetrievalResult(question="q1", chunks=[], elapsed_ms=100, mrr=0, hits=[]),
            RetrievalResult(question="q2", chunks=[], elapsed_ms=200, mrr=0, hits=[]),
        ]
        report = aggregate_report(results, k_values=[1], timestamp="2026-01-01T00:00:00")
        assert report.avg_latency_ms == 150.0
        assert report.total_latency_ms == 300.0

    def test_empty_results(self) -> None:
        report = aggregate_report([], k_values=[1, 3, 5], timestamp="2026-01-01T00:00:00")
        assert report.total == 0
        assert report.mean_mrr == 0.0
        assert report.hit_rate_at_1 == 0.0
