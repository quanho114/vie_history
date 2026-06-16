"""HyDE (Hypothetical Document Embeddings) query expansion.

HyDE generates a hypothetical answer document from the query, embeds it,
then retrieves real chunks that match the hypothetical document. This bridges
the lexical/semantic gap and improves recall by 15-30% on average.

Reference: Gao et al. "Precise Zero-Shot Dense Retrieval without
Controversial Pseudo-Relevance Feedback" (TREC 2022 / ICLR 2023).
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.retrieval.embedder import Embedder

HYDE_PROMPT = """Bạn là một chuyên gia nghiên cứu lịch sử Việt Nam.

Dựa trên câu hỏi dưới đây, hãy viết một đoạn văn trả lời ngắn gọn, chính xác,
đúng như một đoạn trích từ bài viết lịch sử đáng tin cậy.

Câu hỏi: {query}

Hãy viết câu trả lời dưới dạng một đoạn văn bản lịch sử chuẩn xác,
bao gồm các sự kiện, ngày tháng, nhân vật cụ thể nếu có.
Chỉ viết đoạn văn, không viết gì khác:"""


def _build_llm_client() -> Any | None:
    """Build the configured LLM client based on settings."""
    from app.core.config import settings

    if settings.LLM_PROVIDER == "anthropic" and settings.ANTHROPIC_API_KEY:
        from app.services.llm.client import AnthropicClient
        return AnthropicClient()

    if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        from app.services.llm.client import OpenAICompatibleClient
        return OpenAICompatibleClient(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
            model=settings.OPENAI_MODEL,
        )

    if settings.LLM_PROVIDER == "openrouter" and settings.OPENROUTER_API_KEY:
        from app.services.llm.client import OpenAICompatibleClient
        return OpenAICompatibleClient(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=settings.OPENROUTER_BASE_URL,
            model="google/gemini-2.0-flash-thinking-exp",
        )

    if settings.LLM_PROVIDER == "ollama":
        from app.services.llm.client import OllamaClient
        return OllamaClient(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
        )

    return None


class HyDEModule:
    """HyDE expansion using LLM-generated hypothetical documents."""

    def __init__(
        self,
        embedder: Embedder,
        hyde_prompt: str = HYDE_PROMPT,
    ) -> None:
        self.embedder = embedder
        self.hyde_prompt = hyde_prompt
        self._llm_client: Any | None = None

    def _get_llm_client(self) -> Any | None:
        """Lazily build the LLM client on first use."""
        if self._llm_client is None:
            self._llm_client = _build_llm_client()
        return self._llm_client

    async def generate_hypothetical_document(self, query: str) -> str:
        """
        Generate a hypothetical answer document for the query.

        Uses the configured LLM (Anthropic > OpenAI > OpenRouter > Ollama)
        to generate a concise, factual answer that acts as the "ideal document"
        for retrieval. Falls back to returning the original query on failure.
        """
        client = self._get_llm_client()
        if client is None:
            return query

        prompt = self.hyde_prompt.format(query=query)
        try:
            result = await asyncio.wait_for(
                client.generate(prompt=prompt, max_tokens=300),
                timeout=15.0,
            )
            return result.strip() if result else query
        except (asyncio.TimeoutError, Exception):
            return query

    async def embed_hypothetical(self, query: str) -> tuple[str, list[float]]:
        """
        Generate a hypothetical document AND embed it alongside the original query.

        Returns:
            Tuple of (hypothetical_text, hypothetical_embedding)
        """
        hyde_text = await self.generate_hypothetical_document(query)
        hyde_embedding = await self.embedder.embed_async([hyde_text])
        return (
            hyde_text,
            hyde_embedding[0].tolist() if len(hyde_embedding) > 0 else [],
        )

    async def expand_query(self, query: str, top_k: int = 5) -> dict[str, Any]:
        """
        Expand query with HyDE: returns original + hypothetical embeddings.

        Returns a dict with:
            original_query, hypothetical_document, original_vector, hyde_vector
        """
        hyde_text, hyde_vector = await self.embed_hypothetical(query)
        original_embedding = await self.embedder.embed_async([query])
        original_vector = (
            original_embedding[0].tolist() if len(original_embedding) > 0 else []
        )

        return {
            "original_query": query,
            "hypothetical_document": hyde_text,
            "original_vector": original_vector,
            "hyde_vector": hyde_vector,
        }
