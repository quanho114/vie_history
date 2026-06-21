"""Citation verification pipeline using claim extraction and multi-aspect calibrated scoring."""

import re
import numpy as np
from typing import Any, List, Dict, Optional
from app.services.retrieval.embedder import Embedder
from app.services.citation.claim_extractor import ClaimExtractor
from app.services.citation.nli_model import NLIModel
from app.services.citation.nli_verifier import NLIVerifier
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger("citation_verifier")

class CitationVerifier:
    """Verify generated claims against source document chunks using calibrated scoring."""

    def __init__(self, embedder: Optional[Embedder] = None, threshold: float = 0.85, partial_threshold: float = 0.70) -> None:
        self.embedder = embedder or Embedder()
        self.threshold = threshold
        self.partial_threshold = partial_threshold
        self.claim_extractor = ClaimExtractor()
        self.nli_model = NLIModel()
        self.fallback_verifier = NLIVerifier(use_model=False)

    def _split_into_sentences(self, text: str) -> List[str]:
        """Delegate sentence splitting to ClaimExtractor."""
        if not hasattr(self, "claim_extractor") or self.claim_extractor is None:
            self.claim_extractor = ClaimExtractor()
        return self.claim_extractor._split_sentences(text)

    def _calculate_entity_score(self, claim: str, source: str) -> float:
        """Calculate overlap of proper nouns/entities between claim and source."""
        words = claim.strip().split()
        if not words:
            return 1.0

        entities = []
        current_ent = []

        for idx, word in enumerate(words):
            w_clean = re.sub(r"[^\w\s]", "", word)
            if not w_clean:
                continue

            if w_clean[0].isupper() and not w_clean.isdigit():
                if idx == 0 and len(words) > 1:
                    # For the first word, treat as entity if the next word is also capitalized
                    next_w = re.sub(r"[^\w\s]", "", words[1])
                    if next_w and next_w[0].isupper():
                        current_ent.append(w_clean)
                else:
                    current_ent.append(w_clean)
            else:
                if current_ent:
                    entities.append(" ".join(current_ent))
                    current_ent = []
        if current_ent:
            entities.append(" ".join(current_ent))

        # Filter out common Vietnamese words that might be capitalized at sentence start
        filtered_entities = []
        for ent in entities:
            ent_lower = ent.lower()
            if ent_lower in ["không", "nhưng", "tuy", "vì", "tại", "trong", "theo", "dưới", "được", "bị", "sau", "đó"]:
                continue
            if len(ent) > 1:
                filtered_entities.append(ent)

        unique_entities = list(set(filtered_entities))
        if not unique_entities:
            return 1.0

        matched = 0
        source_lower = source.lower()
        for ent in unique_entities:
            if ent.lower() in source_lower:
                matched += 1

        return float(matched / len(unique_entities))

    def _calculate_numeric_score(self, claim: str, source: str) -> float:
        """Verify that all numbers in the claim are present in the source."""
        clean_claim = re.sub(r"\[S\d+\]", "", claim)
        claim_digits = set(re.findall(r"\b\d+\b", clean_claim))

        if not claim_digits:
            return 1.0

        source_digits = set(re.findall(r"\b\d+\b", source))
        if claim_digits.issubset(source_digits):
            return 1.0
        return 0.0

    def _calculate_temporal_score(self, claim: str, source: str) -> float:
        """Verify that all years (4 digits) in the claim are present in the source."""
        clean_claim = re.sub(r"\[S\d+\]", "", claim)
        claim_years = set(re.findall(r"\b\d{4}\b", clean_claim))

        if not claim_years:
            return 1.0

        source_years = set(re.findall(r"\b\d{4}\b", source))
        if claim_years.issubset(source_years):
            return 1.0
        return 0.0

    async def verify(self, answer: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verify the answer against source chunks using multi-aspect calibrated scoring.
        
        Respects ENABLE_VERIFICATION feature flag.
        """
        if not settings.ENABLE_VERIFICATION:
            logger.info("citation_verification_disabled_bypassing")
            return {"verified_answer": answer, "claims": [], "needs_rewrite": False}

        # Extract atomic claims
        atomic_claims = self.claim_extractor.extract_claims(answer)
        if not atomic_claims:
            return {"verified_answer": answer, "claims": [], "needs_rewrite": False}

        claim_texts = [c["text"] for c in atomic_claims]

        # Embed claims
        sentence_embeddings = await self.embedder.embed_async(claim_texts)
        
        # Embed source chunks
        source_texts = [chunk.get("content", "") for chunk in chunks]
        source_embeddings = await self.embedder.embed_async(source_texts) if source_texts else []

        claims_results = []
        needs_rewrite = False

        # Phase 1: Determine matched sources and compute cosine similarities
        matched_indices = []
        similarities = []

        for i, claim in enumerate(atomic_claims):
            text = claim["text"]
            markers = re.findall(r"\[S(\d+)\]", text)
            
            matched_source = None
            max_sim = 0.0

            if markers:
                for marker in markers:
                    idx = int(marker) - 1
                    if 0 <= idx < len(source_embeddings):
                        sim = float(np.dot(sentence_embeddings[i], source_embeddings[idx]))
                        if sim > max_sim or matched_source is None:
                            max_sim = sim
                            matched_source = idx
            else:
                if len(source_embeddings) > 0:
                    sims = np.dot(source_embeddings, sentence_embeddings[i])
                    max_idx = int(np.argmax(sims))
                    max_sim = float(sims[max_idx])
                    matched_source = max_idx

            matched_indices.append(matched_source)
            similarities.append(max_sim)

        # Phase 2: Batch run NLI on matched pairs
        premises = []
        hypotheses = []
        for i, claim in enumerate(atomic_claims):
            matched_source = matched_indices[i]
            claim_text_clean = re.sub(r"\[S\d+\]", "", claim["text"]).strip()
            
            if matched_source is not None and matched_source < len(source_texts):
                source_txt = source_texts[matched_source]
            else:
                source_txt = ""

            premises.append(source_txt)
            hypotheses.append(claim_text_clean)

        nli_probabilities = self.nli_model.verify_batch(premises, hypotheses)

        # Phase 3: Calibrated scoring & Classification
        for i, claim in enumerate(atomic_claims):
            text = claim["text"]
            claim_type = claim["type"]
            matched_source = matched_indices[i]
            max_sim = similarities[i]
            
            has_original_marker = bool(re.findall(r"\[S\d+\]", text))
            claim_text_clean = re.sub(r"\[S\d+\]", "", text).strip()

            if matched_source is not None and matched_source < len(source_texts):
                source_txt = source_texts[matched_source]
            else:
                source_txt = ""

            # Check if source_txt is empty
            if not source_txt:
                status = "unsupported"
                score = 0.0
                nli_score = 0.0
                entity_score = 0.0
                numeric_score = 0.0
                temporal_score = 0.0
            else:
                # Entity, numeric, temporal scores
                entity_score = self._calculate_entity_score(claim_text_clean, source_txt)
                numeric_score = self._calculate_numeric_score(claim_text_clean, source_txt)
                temporal_score = self._calculate_temporal_score(claim_text_clean, source_txt)

                # NLI score
                nli_score = nli_probabilities[i] if i < len(nli_probabilities) else 0.0
                
                # NLI Fallback to heuristic if model not loaded or returned zero
                if not self.nli_model._model_loaded and nli_score == 0.0:
                    nli_score = 1.0 if self.fallback_verifier._verify_heuristic(claim_text_clean, source_txt) else 0.0

                # Calibrated formula
                score = 0.15 * entity_score + 0.15 * numeric_score + 0.10 * temporal_score + 0.60 * nli_score

                # Classify based on score
                if score >= self.threshold:
                    status = "supported"
                elif score >= self.partial_threshold:
                    status = "partially_supported"
                    needs_rewrite = True
                else:
                    status = "unsupported"
                    needs_rewrite = True

            # Auto-attribute citation if it was missing and claim is fully supported
            sentence = text
            if not has_original_marker and status == "supported" and matched_source is not None:
                sentence = f"{claim_text_clean} [S{matched_source + 1}]"

            claims_results.append({
                "sentence": sentence,
                "status": status,
                "similarity": max_sim,
                "matched_source": matched_source,
                "score": score,
                "nli_score": nli_score,
                "entity_score": entity_score,
                "numeric_score": numeric_score,
                "temporal_score": temporal_score,
                "type": claim_type,
            })

        verified_answer = answer
        if needs_rewrite:
            logger.info("citation_rewrite_required", total_claims=len(claims_results))
            verified_answer = await self._rewrite_answer(answer, claims_results, chunks)
        else:
            logger.info("citation_all_claims_supported")
            verified_answer = " ".join([c["sentence"] for c in claims_results])

        return {
            "verified_answer": verified_answer,
            "claims": claims_results,
            "needs_rewrite": needs_rewrite
        }

    async def _rewrite_answer(self, original_answer: str, claims: List[Dict[str, Any]], chunks: List[Dict[str, Any]]) -> str:
        """Use LLM to rewrite answer, dropping or correcting unsupported/partially supported claims."""
        if settings.APP_ENV == "testing":
            # Simple fallback for testing to ensure deterministic results
            corrected = []
            for claim in claims:
                if claim["status"] == "supported":
                    corrected.append(claim["sentence"])
            return " ".join(corrected) if corrected else "Không có thông tin kiểm chứng."

        try:
            from app.services.llm.client import get_llm_client
            client = get_llm_client()
            
            sources_summary = []
            for i, chunk in enumerate(chunks, 1):
                sources_summary.append(f"[S{i}]: {chunk.get('content', '')[:1000]}")
                
            claims_summary = []
            for claim in claims:
                claims_summary.append(f"Câu: '{claim['sentence']}' - Trạng thái: {claim['status'].upper()}")

            prompt = (
                f"Bản gốc câu trả lời:\n{original_answer}\n\n"
                f"Danh sách kiểm chứng từng câu:\n" + "\n".join(claims_summary) + "\n\n"
                f"Dữ liệu nguồn hợp lệ:\n" + "\n\n".join(sources_summary) + "\n\n"
                "Nhiệm vụ của bạn: Hãy viết lại câu trả lời trên. "
                "BẮT BUỘC chỉ được giữ lại thông tin được xác nhận bởi các nguồn hợp lệ. "
                "Xóa bỏ hoàn toàn hoặc sửa đổi các câu bị đánh dấu UNSUPPORTED hoặc PARTIALLY_SUPPORTED "
                "để chúng khớp hoàn toàn với dữ liệu nguồn. "
                "Đảm bảo các câu giữ lại đều có dẫn nguồn chính xác dạng [S1], [S2] ở cuối câu."
            )
            
            system = "Bạn là biên tập viên kiểm chứng lịch sử Việt Nam chuyên nghiệp. Hãy chỉnh sửa câu trả lời chính xác, học thuật và loại bỏ thông tin sai lệch."
            rewritten = await client.generate(prompt, system=system, max_tokens=1200)
            return rewritten
        except Exception as exc:
            logger.warning("citation_llm_rewrite_failed", error=str(exc))
            corrected = []
            for claim in claims:
                if claim["status"] == "supported":
                    corrected.append(claim["sentence"])
            return " ".join(corrected) if corrected else original_answer
