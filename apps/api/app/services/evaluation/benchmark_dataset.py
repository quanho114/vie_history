"""VH-RAG Benchmark: Vietnamese History RAG evaluation dataset.

This benchmark evaluates RAG quality on Vietnamese historical content,
covering key events, figures, and timelines from Vietnamese history.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class BenchmarkQuery:
    """A single benchmark query with expected properties."""
    id: str
    query: str
    category: Literal["event", "figure", "timeline", "location", "policy"]
    difficulty: Literal["simple", "medium", "complex"]
    expected_topics: list[str] = field(default_factory=list)
    ground_truth: str = ""
    query_type: Literal["factual", "analytical", "comparative", "temporal"] = "factual"


class VHRAGBenchmark:
    """Vietnamese History RAG benchmark dataset."""

    VERSION = "1.0.0"

    QUERIES: list[BenchmarkQuery] = [
        BenchmarkQuery(
            id="vhrag_001",
            query="Trình bày diễn biến Chiến dịch Điện Biên Phủ 1954",
            category="event",
            difficulty="complex",
            expected_topics=["Điện Biên Phủ", "Tướng Võ Nguyên Giáp", "Pháp", "Navy française"],
            ground_truth="Chiến dịch Điện Biên Phủ diễn ra từ 13/3/1954 đến 7/5/1954...",
            query_type="analytical",
        ),
        BenchmarkQuery(
            id="vhrag_002",
            query="Ai là người đầu tiên đặt chân lên lãnh thổ Việt Nam?",
            category="figure",
            difficulty="simple",
            expected_topics=["An Dương Vương", "tổ tiên", "lịch sử"],
            ground_truth="Lịch sử Việt Nam ghi nhận nhiều nhân vật...",
            query_type="factual",
        ),
        BenchmarkQuery(
            id="vhrag_003",
            query="So sánh chính sách đô thị hóa thời Pháp thuộc và sau 1945",
            category="policy",
            difficulty="complex",
            expected_topics=["thuộc địa", "đô thị", "Hà Nội", "Sài Gòn"],
            ground_truth="...",
            query_type="comparative",
        ),
        BenchmarkQuery(
            id="vhrag_004",
            query="Các giai đoạn chính của cuộc kháng chiến chống Pháp",
            category="timeline",
            difficulty="medium",
            expected_topics=["kháng chiến", "1945", "1954", "Bến Thuỷ", "Việt Minh"],
            ground_truth="...",
            query_type="temporal",
        ),
        BenchmarkQuery(
            id="vhrag_005",
            query="Đại hội Đảng Lao Động Việt Nam lần thứ I có ý nghĩa gì?",
            category="event",
            difficulty="medium",
            expected_topics=["Đảng Lao Động", "1951", "Trường Chinh", "thống nhất"],
            ground_truth="...",
            query_type="factual",
        ),
    ]

    @classmethod
    def get_queries(cls, category: str | None = None, difficulty: str | None = None) -> list[BenchmarkQuery]:
        results = cls.QUERIES
        if category:
            results = [q for q in results if q.category == category]
        if difficulty:
            results = [q for q in results if q.difficulty == difficulty]
        return results

    @classmethod
    def total_count(cls) -> int:
        return len(cls.QUERIES)
