"""Verifier service."""

from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger("verifier")


@dataclass
class VerificationResult:
    """Result of evidence verification."""

    sufficient: bool
    evidence_count: int
    duplicate_ratio: float
    conflict_detected: bool
    message: str | None = None


class Verifier:
    """
    Verifies retrieved evidence before generating answer.
    """

    def __init__(
        self,
        min_evidence: int = 2,
        max_duplicate_ratio: float = 0.7,
        conflict_threshold: float = 0.3,
    ):
        self.min_evidence = min_evidence
        self.max_duplicate_ratio = max_duplicate_ratio
        self.conflict_threshold = conflict_threshold

    def verify(self, chunks: list[dict], query: str) -> VerificationResult:
        """
        Verify evidence sufficiency.

        Checks:
        1. Minimum evidence count
        2. Duplicate document ratio
        3. Potential conflicts
        """
        if not chunks:
            return VerificationResult(
                sufficient=False,
                evidence_count=0,
                duplicate_ratio=0.0,
                conflict_detected=False,
                message="No evidence found for this query.",
            )

        evidence_count = len(chunks)

        # Check document diversity
        doc_ids = [c.get("document_id") for c in chunks if c.get("document_id")]
        unique_docs = len(set(doc_ids))
        duplicate_ratio = 1 - (unique_docs / len(chunks)) if chunks else 0

        # Check for conflicts (simplified - would need more sophisticated analysis)
        conflict_detected = False

        # Determine sufficiency
        sufficient = (
            evidence_count >= self.min_evidence
            and duplicate_ratio < self.max_duplicate_ratio
            and not conflict_detected
        )

        message = None
        if not sufficient:
            if evidence_count < self.min_evidence:
                message = f"Only {evidence_count} evidence chunks found. Need at least {self.min_evidence}."
            elif duplicate_ratio >= self.max_duplicate_ratio:
                message = "Evidence comes from too few documents. More diverse sources needed."
            elif conflict_detected:
                message = "Conflicting information detected in evidence."

        logger.info(
            "evidence_verified",
            sufficient=sufficient,
            evidence_count=evidence_count,
            duplicate_ratio=duplicate_ratio,
            conflict_detected=conflict_detected,
        )

        return VerificationResult(
            sufficient=sufficient,
            evidence_count=evidence_count,
            duplicate_ratio=duplicate_ratio,
            conflict_detected=conflict_detected,
            message=message,
        )
