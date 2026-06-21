"""NLIVerifier wrapping the cached NLIModel singleton for backwards compatibility."""

import re
from app.core.logging import get_logger
from app.services.citation.nli_model import NLIModel, HAS_TRANSFORMERS

logger = get_logger("nli_verifier")

try:
    import underthesea
    HAS_UNDERTHESEA = True
except ImportError:
    HAS_UNDERTHESEA = False
    logger.warning("underthesea_missing_using_regex_splitter")


class NLIVerifier:
    """Verifies factual entailment using the cached NLIModel singleton."""

    def __init__(self, use_model: bool = True, model_name: str = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli", device: str = "cpu") -> None:
        self.use_model = use_model and HAS_TRANSFORMERS
        self.model_name = model_name
        self.device = device
        self.model = NLIModel(model_name=self.model_name, device=self.device)

    def verify_entailment(self, claim: str, source: str) -> bool:
        """Verifies if the claim is entailed by the source text."""
        # Clean citation markers like [S1], [S2]
        claim_clean = re.sub(r"\[S\d+\]", "", claim).strip()
        source_clean = re.sub(r"\[S\d+\]", "", source).strip()

        if not claim_clean or not source_clean:
            return False

        if self.use_model and self.model._model_loaded:
            try:
                scores = self.model.verify_batch([source_clean], [claim_clean])
                if scores:
                    entailment_prob = scores[0]
                    logger.info("nli_inference_complete", entailment_prob=entailment_prob)
                    return entailment_prob >= 0.5  # Standard threshold
            except Exception as exc:
                logger.error("nli_inference_failed_using_heuristic", error=str(exc))

        return self._verify_heuristic(claim_clean, source_clean)

    def _verify_heuristic(self, claim: str, source: str) -> bool:
        claim_lower = claim.lower()
        source_lower = source.lower()
        
        # Extract potential capitalized entities in Vietnamese from the claim
        words = claim.split()
        entities = []
        current_entity = []
        for w in words:
            w_clean = re.sub(r"[^\w\s]", "", w)
            if not w_clean:
                continue
            if w_clean[0].isupper() and not w_clean.isdigit():
                current_entity.append(w_clean)
            else:
                if current_entity:
                    entities.append(" ".join(current_entity))
                    current_entity = []
        if current_entity:
            entities.append(" ".join(current_entity))
            
        cleaned_entities = []
        for ent in entities:
            ent_lower = ent.lower()
            if ent_lower in ["không", "nhưng", "tuy", "vì", "tại", "trong", "theo", "dưới"]:
                continue
            if len(ent) > 1:
                cleaned_entities.append(ent)
                
        # If any extracted entity is NOT in the source text (case-insensitive), claim is unsupported
        for ent in cleaned_entities:
            ent_clean = ent.lower().strip()
            first_word = claim.strip().split()[0] if claim.strip() else ""
            first_word_clean = re.sub(r"[^\w\s]", "", first_word)
            if ent == first_word_clean and len(ent.split()) == 1:
                continue
            
            if ent_clean not in source_lower:
                return False
                
        return True

    def tokenize_sentences(self, text: str) -> list[str]:
        """Tokenize text into sentences securely."""
        if HAS_UNDERTHESEA:
            try:
                return underthesea.sent_tokenize(text)
            except Exception as exc:
                logger.warning("underthesea_tokenization_failed_using_regex", error=str(exc))
        
        # Safe Regex Splitter protecting common abbreviations like "V.v", "Tp.HCM", "NXB"
        sentences = re.split(r'(?<![A-ZĐ])\.\s+(?=[A-ZĐÁÀẢÃẠÂẤẦẨẪẬĂẮẰẲẴẶÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸY])', text)
        return [s.strip() for s in sentences if s.strip()]
