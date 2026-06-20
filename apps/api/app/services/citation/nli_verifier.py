import re
from app.core.logging import get_logger

logger = get_logger("nli_verifier")

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    logger.warning("transformers_or_torch_missing_nli_uses_heuristic")

try:
    import underthesea
    HAS_UNDERTHESEA = True
except ImportError:
    HAS_UNDERTHESEA = False
    logger.warning("underthesea_missing_using_regex_splitter")


class NLIVerifier:
    """
    Verifies factual entailment of LLM-generated claims against search source texts
    using a multilingual Cross-Encoder NLI model (mDeBERTa-v3-base-mnli-xnli)
    with a heuristic-based fallback mechanism.
    """

    def __init__(self, use_model: bool = True, model_name: str = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli", device: str = "cpu"):
        self.use_model = use_model and HAS_TRANSFORMERS
        self.model_name = model_name
        self.device = device
        self._tokenizer = None
        self._model = None
        self._model_loaded = False

        if self.use_model:
            try:
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name).to(self.device)
                self._model_loaded = True
                logger.info("nli_model_loaded", model=self.model_name, device=self.device)
            except Exception as e:
                logger.warning("nli_model_load_failed_falling_back_to_heuristic", error=str(e))
                self.use_model = False

    def verify_entailment(self, claim: str, source: str) -> bool:
        """
        Verifies if the claim is entailed by the source text.
        Returns True if entailment is found, False otherwise.
        """
        # Clean citation markers like [S1], [S2]
        claim_clean = re.sub(r"\[S\d+\]", "", claim).strip()
        source_clean = re.sub(r"\[S\d+\]", "", source).strip()

        if not claim_clean or not source_clean:
            return False

        if self.use_model and self._model_loaded:
            try:
                # Tokenize premise and hypothesis pair
                inputs = self._tokenizer(source_clean, claim_clean, truncation=True, max_length=512, return_tensors="pt").to(self.device)
                with torch.no_grad():
                    outputs = self._model(**inputs)
                
                # Label indices: 0 = entailment, 1 = neutral, 2 = contradiction
                logits = outputs.logits
                predicted_class = torch.argmax(logits, dim=1).item()
                
                # We also consider strength of classification
                probs = torch.softmax(logits, dim=1)
                entailment_prob = probs[0][0].item()
                
                logger.info("nli_inference_complete", predicted_class=predicted_class, entailment_prob=entailment_prob)
                
                # Return True only if entailment is the top predicted label
                return predicted_class == 0
            except Exception as exc:
                logger.error("nli_inference_failed_using_heuristic", error=str(exc))
                # Fall through to heuristic fallback

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
        # Split on periods followed by space and uppercase character
        sentences = re.split(r'(?<![A-ZĐ])\.\s+(?=[A-ZĐÁÀẢÃẠÂẤẦẨẪẬĂẮẰẲẴẶÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸY])', text)
        return [s.strip() for s in sentences if s.strip()]
