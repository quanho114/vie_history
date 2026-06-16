"""
Complexity Classifier — zero-token, keyword-based query router.

Routes queries to one of three execution modes without any LLM calls:
  - fast    (80–90% traffic): factual, greeting, out_of_scope
  - graph   (10–15% traffic): compare, timeline, relation, multi_hop
  - agentic (1–5%  traffic): causal, geopolitical, deep analysis

This is the architectural entry gate for the entire pipeline.
No LLM is ever called here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger("complexity_classifier")

# ──────────────────────────────────────────────────────────────
# Budget constants (budget-aware agentic)
# ──────────────────────────────────────────────────────────────
MAX_REFLECTION_LOOPS = 1    # critic can trigger replanning at most once
MAX_GRAPH_DEPTH = 2         # Neo4j traversal depth cap
MAX_TOOL_CALLS = 5          # total LLM calls per agentic request
MAX_AGENT_STEPS = 3         # retrieval/graph/timeline nodes max

# Adaptive token budgets per mode
TOKEN_BUDGET: dict[str, int] = {
    "fast": 400,
    "graph": 700,
    "agentic": 1500,
}


@dataclass
class ComplexityResult:
    mode: str           # "fast" | "graph" | "agentic"
    intent: str         # original intent label
    confidence: float   # 0.0–1.0 — keyword signal strength


# ──────────────────────────────────────────────────────────────
# Keyword tables
# ──────────────────────────────────────────────────────────────

_GREETING_PATTERNS = [
    "chào", "hello", "hi", "xin chào", "cảm ơn", "thank", "bye",
    "tạm biệt", "hey", "hola", "good morning", "good evening",
    "chào buổi sáng", "chào buổi tối", "bạn khỏe", "how are you",
    "nice to meet", "rất vui", "giới thiệu bản thân", "tên gì",
    "bạn là ai", "what is your name", "who are you",
]

_FACTUAL_PATTERNS = [
    "là ai", "là gì", "ở đâu", "năm nào", "khi nào", "bao giờ",
    "who is", "what is", "where is", "when was", "which year",
    "tên của", "thành lập", "thành lập năm", "ký kết", "ký năm",
    "sinh năm", "mất năm", "số lượng", "bao nhiêu",
]

_GRAPH_PATTERNS = [
    "so sánh", "compare", "khác nhau", "giống nhau", "giữa",
    "liên quan", "kết nối", "mối liên hệ", "quan hệ", "ảnh hưởng tới",
    "liên kết", "dẫn đến", "tiếp theo sau", "trước khi",
    "timeline", "diễn biến", "trình tự", "theo thứ tự",
    "niên biểu", "giai đoạn", "chuỗi sự kiện",
    "multi_hop", "chain",
]

_AGENTIC_PATTERNS = [
    "tại sao", "vì sao", "nguyên nhân", "hệ quả", "kết quả",
    "why", "cause", "effect", "reason",
    "phân tích", "analyze", "analysis", "đánh giá",
    "địa chính trị", "geopolitical", "chiến lược", "strategy",
    "ảnh hưởng sâu", "tác động lâu dài", "bối cảnh quốc tế",
    "luận điểm", "lập luận", "chứng minh",
    "xác minh", "kiểm tra", "verify", "đúng không", "có phải",
    "mâu thuẫn", "contradiction", "phản bác",
    "suy luận", "reasoning", "inference",
    "đa chiều", "multi-hop", "nhiều góc độ",
]

_OUT_OF_SCOPE_PATTERNS = [
    "2025", "2026", "2027", "hiện nay", "bây giờ", "hôm nay",
    "thời sự", "bóng đá", "kinh tế hiện đại", "covid", "ai tools",
    "chatgpt", "openai", "công nghệ", "lập trình",
]


# ──────────────────────────────────────────────────────────────
# Classifier
# ──────────────────────────────────────────────────────────────

class ComplexityClassifier:
    """
    Keyword-based complexity classifier — zero LLM cost, ~0ms latency.

    Decision priority (highest → lowest):
      1. out_of_scope  → fast (short-circuit, no retrieval)
      2. greeting      → fast
      3. agentic       → agentic  (causal / geopolitical keywords)
      4. graph         → graph    (compare / timeline / relation)
      5. factual       → fast     (default)
    """

    def classify(self, query: str) -> ComplexityResult:
        q = query.lower().strip()
        word_count = len(q.split())

        # ── 1. Out of scope ──────────────────────────────────
        for kw in _OUT_OF_SCOPE_PATTERNS:
            if kw in q:
                logger.info("complexity_classified", mode="fast", intent="out_of_scope", query=query[:60])
                return ComplexityResult(mode="fast", intent="out_of_scope", confidence=0.95)

        # ── 2. Agentic (check BEFORE greeting — causal/geopolitical wins) ─
        agentic_hits = sum(1 for kw in _AGENTIC_PATTERNS if kw in q)
        if agentic_hits >= 1:
            confidence = min(0.7 + agentic_hits * 0.1, 0.99)
            logger.info("complexity_classified", mode="agentic", intent="causal_analysis",
                       hits=agentic_hits, query=query[:60])
            return ComplexityResult(mode="agentic", intent="causal_analysis", confidence=confidence)

        # ── 3. Graph (check BEFORE greeting — relational queries win) ─────
        graph_hits = sum(1 for kw in _GRAPH_PATTERNS if kw in q)
        if graph_hits >= 1:
            confidence = min(0.65 + graph_hits * 0.1, 0.95)
            logger.info("complexity_classified", mode="graph", intent="relational",
                       hits=graph_hits, query=query[:60])
            return ComplexityResult(mode="graph", intent="relational", confidence=confidence)

        # ── 4. Greeting (only pure social messages, short) ───────────────
        if word_count <= 8:
            q_clean = q
            for p in ".,!?;:":
                q_clean = q_clean.replace(p, " ")
            words = q_clean.split()
            for kw in _GREETING_PATTERNS:
                if " " in kw:
                    if kw in q:
                        logger.info("complexity_classified", mode="fast", intent="greeting", query=query[:60])
                        return ComplexityResult(mode="fast", intent="greeting", confidence=0.98)
                else:
                    if kw in words:
                        logger.info("complexity_classified", mode="fast", intent="greeting", query=query[:60])
                        return ComplexityResult(mode="fast", intent="greeting", confidence=0.98)

        # ── 5. Factual / default ──────────────────────────────────────────
        factual_hits = sum(1 for kw in _FACTUAL_PATTERNS if kw in q)
        confidence = min(0.6 + factual_hits * 0.1, 0.90)
        logger.info("complexity_classified", mode="fast", intent="factual", query=query[:60])
        return ComplexityResult(mode="fast", intent="factual", confidence=confidence)


# Module-level singleton — import and call directly
_classifier = ComplexityClassifier()


def classify_complexity(query: str) -> ComplexityResult:
    """Convenience function. Zero LLM cost, ~0ms."""
    return _classifier.classify(query)
