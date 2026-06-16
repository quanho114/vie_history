"""RAG Evaluator using RAGAS-inspired metrics."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Protocol


class RAGMetrics(Protocol):
    """Protocol for RAG evaluation metrics."""
    faithfulness: float
    answer_relevancy: float
    context_precision: float
    citation_recall: float
    citation_precision: float


@dataclass
class EvaluationResult:
    """Result of evaluating a single RAG query response."""
    query_id: str
    query: str
    generated_answer: str
    reference_answer: str

    # Metric scores (0.0 - 1.0)
    faithfulness: float = 0.0
    answer_relevancy: float = 0.0
    context_precision: float = 0.0
    citation_recall: float = 0.0
    citation_precision: float = 0.0

    # Overall
    @property
    def overall_score(self) -> float:
        return (
            self.faithfulness * 0.3 +
            self.answer_relevancy * 0.3 +
            self.context_precision * 0.2 +
            self.citation_recall * 0.2
        )


class RAGEvaluator:
    """Evaluate RAG pipeline outputs against ground truth.

    Uses heuristic-based metrics (suitable for offline evaluation
    without LLM-as-judge API calls).
    """

    def evaluate(self, result: EvaluationResult) -> EvaluationResult:
        """Compute all metrics for a single result."""
        result.faithfulness = self._faithfulness(result.generated_answer, result.reference_answer)
        result.answer_relevancy = self._answer_relevancy(result.generated_answer, result.query)
        result.context_precision = self._context_precision(result.generated_answer)
        result.citation_recall = self._citation_recall(result.generated_answer, result.reference_answer)
        result.citation_precision = self._citation_precision(result.generated_answer)
        return result

    def _faithfulness(self, answer: str, reference: str) -> float:
        """Check factual overlap between answer and reference."""
        if not reference:
            return 0.0
        import re
        # Simple token overlap
        ans_tokens = set(re.findall(r'\w+', answer.lower()))
        ref_tokens = set(re.findall(r'\w+', reference.lower()))
        if not ans_tokens:
            return 0.0
        overlap = len(ans_tokens & ref_tokens) / len(ans_tokens)
        return min(overlap, 1.0)

    def _answer_relevancy(self, answer: str, query: str) -> float:
        """Heuristic: answer contains query terms."""
        import re
        query_terms = set(re.findall(r'\w{4,}', query.lower()))
        answer_terms = set(re.findall(r'\w+', answer.lower()))
        if not query_terms:
            return 1.0
        overlap = len(query_terms & answer_terms) / len(query_terms)
        return min(overlap, 1.0)

    def _context_precision(self, answer: str) -> float:
        """Heuristic: answer has reasonable length."""
        words = len(answer.split())
        if words < 10:
            return 0.0
        if words < 50:
            return 0.5
        if words < 200:
            return 0.8
        return 1.0

    def _citation_recall(self, answer: str, reference: str) -> float:
        """Check if answer cites document sources."""
        import re
        has_citation = bool(re.search(r'\[.*?\]|\(.*?\)|{{.*?}}', answer))
        return 1.0 if has_citation else 0.3

    def _citation_precision(self, answer: str) -> float:
        """Check citation format quality."""
        import re
        citations = re.findall(r'\[.*?\]|\(.*?\)|{{.*?}}', answer)
        if not citations:
            return 0.0
        # Check if citations look like valid IDs
        valid = sum(1 for c in citations if re.search(r'[a-zA-Z0-9]{8,}', c))
        return valid / len(citations) if citations else 0.0

    async def evaluate_batch(self, results: list[EvaluationResult]) -> list[EvaluationResult]:
        """Evaluate multiple results."""
        return [self.evaluate(r) for r in results]
