"""NLI Model Singleton wrapper for sentence-level semantic entailment verification."""

from app.core.logging import get_logger

logger = get_logger("nli_model")

try:
    import torch
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False
    logger.warning("transformers_or_torch_missing_nli_uses_heuristic_fallback")


class NLIModel:
    """Singleton wrapper for MoritzLaurer/mDeBERTa-v3-base-mnli-xnli model loading and batch inference."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, model_name: str = "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli", device: str | None = None, cache_path: str = "storage/nli_cache.db") -> None:
        if self._initialized:
            return

        self.model_name = model_name
        self.device = device or ("cuda" if HAS_TRANSFORMERS and torch.cuda.is_available() else "cpu")
        self._tokenizer = None
        self._model = None
        self._model_loaded = False

        from app.services.citation.nli_cache import NLICache
        self._cache = NLICache(cache_file_path=cache_path)

        if HAS_TRANSFORMERS:
            try:
                logger.info("nli_model_loading_started", model=self.model_name, device=self.device)
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self._model = AutoModelForSequenceClassification.from_pretrained(self.model_name).to(self.device)
                self._model_loaded = True
                logger.info("nli_model_loaded_successfully", model=self.model_name, device=self.device)
            except Exception as e:
                logger.warning("nli_model_load_failed_falling_back_to_heuristic", error=str(e))
                self._model_loaded = False
        else:
            self._model_loaded = False

        self._initialized = True

    def verify_batch(self, premises: list[str], hypotheses: list[str]) -> list[float]:
        """Runs batch NLI inference returning entailment probabilities (0.0 to 1.0) for each pair, using NLICache."""
        if not premises or not hypotheses:
            return []

        results = [0.0] * len(premises)
        miss_indices = []
        miss_premises = []
        miss_hypotheses = []

        # 1. Check cache first
        for i in range(len(premises)):
            premise = premises[i]
            hypothesis = hypotheses[i]
            cached_score = self._cache.get(premise, hypothesis)
            if cached_score is not None:
                results[i] = cached_score
            else:
                miss_indices.append(i)
                miss_premises.append(premise)
                miss_hypotheses.append(hypothesis)

        # 2. Run inference on cache misses
        if miss_premises:
            if not self._model_loaded or not HAS_TRANSFORMERS:
                # Fallback score is 0.0
                for idx in miss_indices:
                    results[idx] = 0.0
            else:
                try:
                    inputs = self._tokenizer(
                        miss_premises,
                        miss_hypotheses,
                        truncation=True,
                        max_length=512,
                        padding=True,
                        return_tensors="pt"
                    ).to(self.device)

                    with torch.no_grad():
                        outputs = self._model(**inputs)

                    logits = outputs.logits
                    probs = torch.softmax(logits, dim=1)
                    # Label index 0 is entailment (based on MoritzLaurer models)
                    entailment_probs = probs[:, 0].tolist()

                    # Store new results in cache and final results
                    for k, idx in enumerate(miss_indices):
                        score = entailment_probs[k]
                        results[idx] = score
                        self._cache.set(premises[idx], hypotheses[idx], score)
                except Exception as exc:
                    logger.error("nli_batch_inference_failed", error=str(exc))
                    # Retain 0.0 for failed inferences

        return results
