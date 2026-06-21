"""Claim extraction service to split compound sentences into atomic typed claims."""

import re
from typing import List, Dict, Any

# Common Vietnamese conjunctions to split compound sentences
CONJUNCTIONS = [
    r"\s+và\s+",
    r"\s+nhưng\s+",
    r"\s+đồng thời\s+",
    r"\s+song\s+",
    r"\s+tuy nhiên\s+",
    r"\s+nhưng cũng\s+",
    r"\s+đồng thời cũng\s+",
]

# Pattern matching citation markers like [S1], [S2]
CITATION_RE = re.compile(r"\[S\d+\]")

class ClaimExtractor:
    """Extract atomic claims from a text paragraph, type them, and output structured records."""

    def __init__(self) -> None:
        pass

    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences, protecting abbreviations and respecting citation markers."""
        if not text:
            return []

        abbreviations = ["TP", "ThS", "TS", "GS", "tr", "Q", "PGS", "NXB", "đ", "v.v"]
        protected_text = text
        for abbr in abbreviations:
            protected_text = re.sub(
                rf"\b{abbr}\.",
                f"{abbr}_DOT_TEMP",
                protected_text,
                flags=re.IGNORECASE,
            )

        # Split at sentence boundaries
        pattern = r'(?<=[\.\?\!])\s+(?!\[S\d+\])|(?<=[\.\?\!]\s\[S\d\])\s+|(?<=[\.\?\!]\s\[S\d\d\])\s+'
        raw_sentences = re.split(pattern, protected_text)

        sentences = []
        for s in raw_sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            for abbr in abbreviations:
                s_clean = re.sub(
                    rf"{abbr}_DOT_TEMP",
                    f"{abbr}.",
                    s_clean,
                    flags=re.IGNORECASE,
                )
            sentences.append(s_clean)

        return sentences

    def _extract_subject(self, text: str) -> str:
        """Extract a proper noun or noun phrase subject from the start of the clause."""
        # Clean leading non-alphanumeric chars
        cleaned = re.sub(r"^[^\w\s]+", "", text).strip()
        if not cleaned:
            return ""

        words = cleaned.split()
        subject_words = []
        
        # Take consecutive capitalized words or common title prefixes
        prefixes = {"nhà", "vua", "hoàng", "đế", "chủ", "tịch", "tướng", "quân", "nghĩa"}
        for i, word in enumerate(words):
            word_clean = re.sub(r"[^\w\s]", "", word)
            if not word_clean:
                continue
            
            # Capitalized word or part of title prefix
            if word_clean[0].isupper() or word_clean.lower() in prefixes:
                subject_words.append(word)
            else:
                break

        return " ".join(subject_words) if subject_words else ""

    def _infer_type(self, claim: str) -> str:
        """Infer type of claim (event, actor, location, temporal, concept)."""
        claim_lower = claim.lower()

        # 1. Temporal
        if re.search(r"\b\d{4}\b", claim_lower) or any(t in claim_lower for t in ["năm", "thế kỷ", "ngày", "tháng"]):
            return "temporal"

        # 2. Actor
        actor_keywords = ["ông", "bà", "vua", "tướng", "hoàng đế", "chủ tịch", "lãnh tụ", "nhà thơ", "nhà sử học", "nhân vật"]
        if any(f" {kw} " in f" {claim_lower} " for kw in actor_keywords):
            return "actor"

        # 3. Location
        location_keywords = ["tại", "ở", "sông", "núi", "địa phận", "thành", "tỉnh", "huyện", "nước", "quốc gia", "vùng"]
        if any(f" {kw} " in f" {claim_lower} " for kw in location_keywords):
            return "location"

        # 4. Concept vs Event
        concept_keywords = ["định nghĩa", "khái niệm", "là một", "ý nghĩa", "quan điểm", "chủ trương"]
        if any(kw in claim_lower for kw in concept_keywords):
            return "concept"

        return "event"

    def extract_claims(self, text: str) -> List[Dict[str, Any]]:
        """Process paragraph, split into atomic claims, classify, and return structured list."""
        sentences = self._split_sentences(text)
        extracted_claims = []

        for sentence in sentences:
            # Preserve citation markers if any
            markers = CITATION_RE.findall(sentence)
            marker_suffix = " " + " ".join(markers) if markers else ""
            
            # Clean sentence from citation markers for claim splitting
            clean_sentence = CITATION_RE.sub("", sentence).strip()

            # Attempt to split compound sentence using conjunctions
            clauses = [clean_sentence]
            for conj in CONJUNCTIONS:
                new_clauses = []
                for clause in clauses:
                    split_parts = re.split(conj, clause)
                    if len(split_parts) > 1:
                        # Re-join with the conjunction indicator or treat as separate claims
                        for idx, part in enumerate(split_parts):
                            p = part.strip()
                            if p:
                                new_clauses.append(p)
                    else:
                        new_clauses.append(clause)
                clauses = new_clauses

            # Reconstruct and assign subjects if split
            subject = ""
            for idx, clause in enumerate(clauses):
                clause_clean = clause.strip()
                if not clause_clean:
                    continue

                if idx == 0:
                    subject = self._extract_subject(clause_clean)
                    claim_text = clause_clean
                else:
                    # If second clause starts with a lowercase letter or common verb/preposition, prepend subject
                    first_word = clause_clean.split()[0] if clause_clean.split() else ""
                    is_lowercase = first_word and first_word[0].islower()
                    
                    common_action_prefixes = ["đã", "đang", "sẽ", "được", "bị", "làm", "đánh", "lên", "rút", "ký", "thành"]
                    starts_with_verb = first_word.lower() in common_action_prefixes

                    if (is_lowercase or starts_with_verb) and subject:
                        # Avoid duplicating subject if already present
                        if not clause_clean.lower().startswith(subject.lower()):
                            claim_text = f"{subject} {clause_clean}"
                        else:
                            claim_text = clause_clean
                    else:
                        claim_text = clause_clean
                        # Update current subject context
                        new_sub = self._extract_subject(clause_clean)
                        if new_sub:
                            subject = new_sub

                # Append citation suffix back after stripping text and trailing punctuation
                claim_text_clean = claim_text.strip().rstrip(".?!")
                claim_text_with_marker = f"{claim_text_clean}{marker_suffix}"

                extracted_claims.append({
                    "text": claim_text_with_marker,
                    "type": self._infer_type(claim_text_clean),
                })

        return extracted_claims
