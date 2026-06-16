"""Model cards documenting embedding and reranker models used in the pipeline."""

EMBEDDING_MODEL_CARD = {
    "model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "task": "Semantic search / dense retrieval",
    "languages": ["vi", "en", "multi"],
    "max_seq_length": 256,
    "dimension": 384,
    "pooling": "mean",
    "finetuning": False,
    "source": "HuggingFace",
    "license": "Apache-2.0",
    "note": "Lightweight multilingual model; consider upgrading to larger models for production",
}

RERANKER_MODEL_CARD = {
    "model_name": "cross-encoder/ms-marco-MiniLM-L-12-v2",
    "task": "Cross-encoder reranking",
    "languages": ["en", "multi"],
    "max_seq_length": 512,
    "note": "English-focused; Vietnamese reranking uses BM25 + keyword match as fallback",
}

__all__ = ["EMBEDDING_MODEL_CARD", "RERANKER_MODEL_CARD"]
