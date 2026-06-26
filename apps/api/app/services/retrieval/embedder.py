"""Embedding service using sentence-transformers."""

import os
from typing import Any

import numpy as np

from app.core.config import settings
from app.core.logging import get_logger

# Disable tokenizer parallelism to prevent fork-bomb subprocess spawning
# that saturates CPU/RAM and blocks the uvicorn event loop under memory pressure.
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("MKL_NUM_THREADS", "2")

logger = get_logger("embedder")


_GLOBAL_MODEL = None


class Embedder:
    """
    Text embedding service using sentence-transformers.
    Supports multilingual models for Vietnamese text.
    """

    def __init__(
        self,
        model_name: str | None = None,
        device: str | None = None,
        batch_size: int = 32,
    ):
        self.model_name = model_name or settings.EMBEDDING_MODEL
        self.batch_size = batch_size or 8  # Small batch to avoid spawning DataLoader workers
        
        if device is None:
            try:
                import torch
                if torch.cuda.is_available():
                    self.device = "cuda"
                elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
                    self.device = "mps"
                else:
                    self.device = "cpu"
            except ImportError:
                self.device = "cpu"
        else:
            self.device = device

    async def load(self) -> None:
        """Load the embedding model."""
        global _GLOBAL_MODEL
        if _GLOBAL_MODEL is None:
            logger.info("loading_embedder", model=self.model_name)
            from sentence_transformers import SentenceTransformer
            _GLOBAL_MODEL = SentenceTransformer(self.model_name, device=self.device)
            logger.info("embedder_loaded", model=self.model_name)

    @property
    def model(self):
        """Get the model (lazy loading)."""
        global _GLOBAL_MODEL
        if _GLOBAL_MODEL is None:
            logger.info("lazy_loading_embedder", model=self.model_name)
            from sentence_transformers import SentenceTransformer
            _GLOBAL_MODEL = SentenceTransformer(self.model_name, device=self.device)
            logger.info("lazy_embedder_loaded", model=self.model_name)
        return _GLOBAL_MODEL

    def embed(self, texts: list[str]) -> np.ndarray:
        """
        Generate embeddings for texts.

        Args:
            texts: List of text strings to embed

        Returns:
            numpy array of embeddings (num_texts x embedding_dim)
        """
        if not texts:
            return np.array([])

        embeddings = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,  # L2 normalized for cosine similarity
            # num_workers=0 prevents PyTorch DataLoader from spawning subprocesses
            # which would consume ~2GB RAM and 85% CPU, blocking the entire server
        )
        return embeddings

    async def embed_async(self, texts: list[str]) -> np.ndarray:
        """
        Async wrapper for embed.

        Note: sentence-transformers doesn't have native async,
        so we run in executor to avoid blocking.
        """
        import asyncio

        if not texts:
            return np.array([])

        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(
            None,
            self.embed,
            texts,
        )
        return embeddings

    def get_dimension(self) -> int:
        """Get embedding dimension."""
        return settings.EMBEDDING_DIMENSION
