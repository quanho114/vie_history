"""Citation verification pipeline."""

import re
import numpy as np
from typing import Any, List, Dict
from app.services.retrieval.embedder import Embedder
from app.core.logging import get_logger
from app.core.config import settings

logger = get_logger("citation_verifier")

class CitationVerifier:
    """Verify generated claims against source document chunks using sentence embeddings."""

    def __init__(self, embedder: Embedder | None = None) -> None:
        self.embedder = embedder or Embedder()

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences, keeping track of original content."""
        if not text:
            return []

        # Common Vietnamese abbreviations to protect from splitting
        abbreviations = ["TP", "ThS", "TS", "GS", "tr", "Q", "PGS", "NXB", "đ", "v.v"]
        
        protected_text = text
        for abbr in abbreviations:
            # Match whole-word abbreviation followed by a dot
            protected_text = re.sub(
                rf"\b{abbr}\.",
                f"{abbr}_DOT_TEMP",
                protected_text,
                flags=re.IGNORECASE,
            )

        # Split at sentence boundaries:
        # 1. Dot, question, or exclamation mark followed by space, unless followed by a citation marker [S1]
        # 2. Space after a 1-digit or 2-digit citation marker [S1]/[S12] if it was preceded by a boundary
        pattern = r'(?<=[\.\?\!])\s+(?!\[S\d+\])|(?<=[\.\?\!]\s\[S\d\])\s+|(?<=[\.\?\!]\s\[S\d\d\])\s+'
        raw_sentences = re.split(pattern, protected_text)

        sentences = []
        for s in raw_sentences:
            s_clean = s.strip()
            if not s_clean:
                continue
            # Restore the protected dots
            for abbr in abbreviations:
                s_clean = re.sub(
                    rf"{abbr}_DOT_TEMP",
                    f"{abbr}.",
                    s_clean,
                    flags=re.IGNORECASE,
                )
            sentences.append(s_clean)

        return sentences

    async def verify(self, answer: str, chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Verify the answer against source chunks.
        
        Returns a dict:
            verified_answer: rewritten or validated answer
            claims: list of verified claims and their statuses
            needs_rewrite: boolean indicating if any claim was unsupported
        """
        sentences = self._split_into_sentences(answer)
        if not sentences:
            return {"verified_answer": answer, "claims": [], "needs_rewrite": False}

        # Embed all sentences
        sentence_embeddings = await self.embedder.embed_async(sentences)
        
        # Embed all source chunks
        source_texts = [chunk.get("content", "") for chunk in chunks]
        source_embeddings = await self.embedder.embed_async(source_texts)

        claims = []
        needs_rewrite = False

        for i, sentence in enumerate(sentences):
            # Parse source markers (e.g., [S1], [S2])
            markers = re.findall(r"\[S(\d+)\]", sentence)
            
            status = "unsupported"
            max_sim = 0.0
            matched_source = None

            if markers:
                for marker in markers:
                    idx = int(marker) - 1
                    if 0 <= idx < len(source_embeddings):
                        # Cosine similarity (dot product of L2 normalized vectors)
                        sim = float(np.dot(sentence_embeddings[i], source_embeddings[idx]))
                        if sim > max_sim:
                            max_sim = sim
                            matched_source = idx

                # Classify based on similarity
                if max_sim >= 0.75:
                    status = "supported"
                elif max_sim >= 0.60:
                    status = "partially_supported"
                    needs_rewrite = True
                else:
                    status = "unsupported"
                    needs_rewrite = True
            else:
                # No citation marker -> check overall support against any source chunk
                if len(source_embeddings) > 0:
                    similarities = np.dot(source_embeddings, sentence_embeddings[i])
                    max_idx = int(np.argmax(similarities))
                    max_sim = float(similarities[max_idx])
                    if max_sim >= 0.75:
                        status = "supported"
                        matched_source = max_idx
                        # Auto-attribute citation
                        sentence = f"{sentence} [S{max_idx + 1}]"
                    else:
                        status = "unsupported"
                        needs_rewrite = True
                else:
                    status = "unsupported"
                    needs_rewrite = True

            # If the claim was classified as supported or partially_supported, run strict numerical/entity checks
            if status in ("supported", "partially_supported") and matched_source is not None:
                source_txt = source_texts[matched_source]
                
                # Check numbers (exclude citation markers)
                claim_nums_text = re.sub(r"\[S\d+\]", "", sentence)
                claim_nums = set(re.findall(r"\b\d+\b", claim_nums_text))
                source_nums = set(re.findall(r"\b\d+\b", source_txt))
                
                if not claim_nums.issubset(source_nums):
                    status = "unsupported"
                    needs_rewrite = True
                else:
                    from app.services.citation.nli_verifier import NLIVerifier
                    nli = NLIVerifier()
                    if not nli.verify_entailment(sentence, source_txt):
                        status = "unsupported"
                        needs_rewrite = True

            claims.append({
                "sentence": sentence,
                "status": status,
                "similarity": max_sim,
                "matched_source": matched_source
            })

        verified_answer = answer
        if needs_rewrite:
            logger.info("citation_rewrite_required", total_claims=len(claims))
            verified_answer = await self._rewrite_answer(answer, claims, chunks)
        else:
            logger.info("citation_all_claims_supported")
            # If any claims were auto-attributed, construct verified_answer
            verified_answer = " ".join([c["sentence"] for c in claims])

        return {
            "verified_answer": verified_answer,
            "claims": claims,
            "needs_rewrite": needs_rewrite
        }

    async def _rewrite_answer(self, original_answer: str, claims: List[Dict[str, Any]], chunks: List[Dict[str, Any]]) -> str:
        """Use LLM to rewrite answer, dropping or correcting unsupported/partially supported claims."""
        # Check settings for test env bypass
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
            # Safe fallback: only keep supported claims
            corrected = []
            for claim in claims:
                if claim["status"] == "supported":
                    corrected.append(claim["sentence"])
            return " ".join(corrected) if corrected else original_answer
