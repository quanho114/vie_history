"""Standardized schemas for citation verification and claim status representation."""

from typing import List, Optional
from pydantic import BaseModel, Field

class AtomicClaim(BaseModel):
    """Represents a single atomic claim extracted from the generated answer."""
    text: str = Field(description="The cleaned text of the claim.")
    type: str = Field(description="Claim type: event, actor, location, temporal, or concept.")

class ClaimVerification(BaseModel):
    """Verification results for a single atomic claim."""
    claim: AtomicClaim
    status: str = Field(description="Verdict status: supported, partially_supported, or unsupported.")
    score: float = Field(description="Calibrated final verification score (0.0 to 1.0).")
    nli_score: float = Field(description="Raw or calibrated NLI entailment score.")
    entity_score: float = Field(description="Entity coverage overlap score.")
    numeric_score: float = Field(description="Numeric check score (0.0 or 1.0).")
    temporal_score: float = Field(description="Temporal match score (0.0 or 1.0).")
    matched_source: Optional[int] = Field(default=None, description="Index of the matched source document chunk.")
    similarity: float = Field(default=0.0, description="Embedding cosine similarity score.")

class VerificationReport(BaseModel):
    """Verification report for a synthesized answer."""
    verified_answer: str = Field(description="The verified, potentially rewritten answer with source markers.")
    claims: List[ClaimVerification] = Field(description="List of verified atomic claims and scores.")
    needs_rewrite: bool = Field(description="Boolean flag indicating if any claim was unsupported or partially supported.")
