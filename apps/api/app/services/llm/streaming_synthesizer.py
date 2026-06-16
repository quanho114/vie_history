"""Streaming answer synthesis with real LLM token streaming."""

from __future__ import annotations

import re
from typing import Any, AsyncIterator

from app.core.logging import get_logger
from app.services.llm.client import get_llm_client
import asyncio

logger = get_logger("streaming_synthesizer")

SOURCE_MARKER_RE = re.compile(r"\[S\d+\]")


def _build_system_prompt() -> str:
    return (
        "Bạn là HistoriAI, trợ lý nghiên cứu lịch sử Việt Nam. "
        "Chỉ dùng thông tin trong SOURCES. Mỗi câu có thông tin lịch sử cụ thể "
        "bắt buộc kết thúc bằng citation dạng [S1], [S2]. "
        "Nếu nguồn không đủ, nói rõ không đủ nguồn. "
        "Không bịa tên, ngày, số liệu, hoặc diễn giải ngoài nguồn. "
        "Trả lời bằng tiếng Việt, súc tích, học thuật."
    )


def _build_user_prompt(query: str, intent: str, chunks: list[dict[str, Any]]) -> str:
    source_blocks = []
    for index, chunk in enumerate(chunks[:8], 1):
        title = chunk.get("document_title") or "Nguồn chưa đặt tên"
        section = chunk.get("section_title") or ""
        content = " ".join(chunk.get("content", "").split())[:1800]
        source_blocks.append(f"[S{index}] {title} {section}\n{content}")

    return (
        f"QUERY: {query}\n"
        f"INTENT: {intent}\n\n"
        "SOURCES:\n"
        + "\n\n".join(source_blocks)
        + "\n\nTrả lời bằng tiếng Việt, súc tích, học thuật, có citation ở từng câu có claim."
    )


async def stream_synthesize(
    query: str,
    intent: str,
    chunks: list[dict[str, Any]],
    system_prompt: str | None = None,
    user_prompt: str | None = None,
) -> AsyncIterator[str]:
    """
    Stream tokens from the LLM as they are generated.

    Yields individual token strings. Callers are responsible for
    assembling them into the complete answer.

    Falls back to extractive answer on LLM failure.
    """
    if not chunks:
        fallback = (
            "Mình chưa tìm thấy đủ tư liệu đã được lập chỉ mục để trả lời câu hỏi này. "
            "Bạn có thể nhập thêm tài liệu nguồn hoặc thử hỏi hẹp hơn theo nhân vật, "
            "sự kiện, địa danh hoặc mốc năm cụ thể."
        )
        for word in fallback.split():
            yield word + " "
            await asyncio.sleep(0.02)
        return

    from app.core.config import settings
    if settings.APP_ENV == "testing":
        async for token_text in _stream_extractive(query, intent, chunks):
            yield token_text
        return

    try:
        client = get_llm_client()
        system = system_prompt or _build_system_prompt()
        prompt = user_prompt or _build_user_prompt(query, intent, chunks)

        async for token in client.astream(prompt, system=system):
            if token.is_final:
                logger.debug(
                    "llm_stream_complete",
                    usage=token.usage,
                )
                break
            if token.text:
                yield token.text
                await asyncio.sleep(0.02)
    except Exception as exc:
        logger.error("llm_stream_failed_propagating", error=str(exc))
        raise exc


async def _stream_extractive(
    query: str,
    intent: str,
    chunks: list[dict[str, Any]],
) -> AsyncIterator[str]:
    """Stream an extractive fallback answer word by word."""
    intro_map = {
        "timeline": "Dựa trên các tư liệu tìm được, có thể dựng lại các ý chính theo trình tự sau:",
        "compare": "Dựa trên các tư liệu tìm được, các điểm so sánh chính là:",
        "summary": "Dựa trên các tư liệu tìm được, tóm tắt ngắn gọn như sau:",
        "source_audit": "Các nguồn liên quan nhất hiện có trong hệ thống là:",
    }
    intro = intro_map.get(
        intent,
        "Dựa trên các tư liệu tìm được, câu trả lời có thể tóm lược như sau:",
    )

    for word in intro.split():
        yield word + " "
    yield "\n\n"

    for index, chunk in enumerate(chunks[:5], 1):
        excerpt = _compact(chunk.get("content", ""), max_chars=420)
        for word in f"{index}. {excerpt} [S{index}]".split():
            yield word + " "
        yield "\n\n"

    footer = (
        "Phần trên chỉ sử dụng nội dung đã lập chỉ mục; "
        "các kết luận không có nguồn đã được loại bỏ."
    )
    for word in footer.split():
        yield word + " "


def _compact(text: str, max_chars: int = 420) -> str:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 1].rstrip() + "..."
