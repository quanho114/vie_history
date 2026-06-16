"""Context Composer — assembles a structured context string from multi-brain results."""

from __future__ import annotations

from typing import Any


class ContextComposer:
    """
    Merges results from WikiBrain, TimelineBrain, GraphBrain, and the
    traditional vector/RAG pipeline into a single, well-structured context
    string that is passed to the LLM synthesizer.

    Also provides ``compose_system_prompt`` so each intent gets a tailored
    Vietnamese instruction prefix.
    """

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def compose(
        self,
        query: str,
        intent: str,
        wiki_results: list[dict],
        timeline_results: list[dict],
        graph_results: dict,
        vector_results: list[dict],
    ) -> str:
        """
        Build a structured context string for the LLM.

        Sections are emitted only when the corresponding result set is
        non-empty, so the context stays concise.
        """
        parts: list[str] = []

        # --- Wiki / knowledge-page section ---
        if wiki_results:
            parts.append("=== TÓM TẮT WIKI ===")
            for page in wiki_results[:3]:
                title = page.get("title", "")
                summary = page.get("summary", "")
                parts.append(f"**{title}**")
                if summary:
                    parts.append(summary)

                content: dict[str, Any] = page.get("content") or {}
                if content.get("causes"):
                    parts.append(f"Nguyên nhân: {_flatten(content['causes'])}")
                if content.get("results"):
                    parts.append(f"Kết quả: {_flatten(content['results'])}")
                if content.get("significance"):
                    parts.append(f"Ý nghĩa: {_flatten(content['significance'])}")
                if content.get("background"):
                    parts.append(f"Bối cảnh: {_str_trunc(content['background'], 300)}")

        # --- Timeline section ---
        if timeline_results:
            parts.append("\n=== MỐC THỜI GIAN ===")
            sorted_events = sorted(
                timeline_results,
                key=lambda e: (e.get("start_year") or 0, e.get("event_name", "")),
            )
            for event in sorted_events:
                year_str = str(event.get("start_year", "?"))
                end_year = event.get("end_year")
                if end_year and end_year != event.get("start_year"):
                    year_str += f"–{end_year}"
                event_name = event.get("event_name", "")
                summary = event.get("summary", "")
                line = f"- {year_str}: {event_name}"
                if summary:
                    line += f" — {summary[:200]}"
                parts.append(line)

        # --- Graph / relationship section ---
        if graph_results and (
            graph_results.get("nodes") or graph_results.get("paths")
        ):
            parts.append("\n=== QUAN HỆ LỊCH SỬ ===")
            paths = graph_results.get("paths") or []
            for path in paths[:2]:
                if path:
                    parts.append(f"Mối quan hệ: {path}")

            nodes = graph_results.get("nodes") or []
            for node in nodes[:5]:
                name = node.get("name", "")
                ntype = node.get("node_type", node.get("type", ""))
                desc = node.get("description", node.get("summary", ""))[:200]
                entry = f"- {name}"
                if ntype:
                    entry += f" ({ntype})"
                if desc:
                    entry += f": {desc}"
                parts.append(entry)

        # --- Vector / RAG chunk section ---
        if vector_results:
            parts.append("\n=== BẰNG CHỨNG NGUỒN ===")
            for i, chunk in enumerate(vector_results[:5], 1):
                source = (
                    chunk.get("source_title")
                    or chunk.get("document_title")
                    or f"Nguồn {i}"
                )
                content_text = chunk.get("content") or chunk.get("text") or ""
                excerpt = content_text[:300].rstrip()
                if len(content_text) > 300:
                    excerpt += "..."
                parts.append(f"[{i}] {source}: {excerpt}")

        return "\n".join(parts)

    def compose_system_prompt(self, intent: str) -> str:
        """Return an intent-specific system prompt in Vietnamese."""
        base = (
            "Bạn là chuyên gia lịch sử Việt Nam giai đoạn 1945–1975, tên HistoriAI. "
            "Hãy trả lời chính xác, có cấu trúc và trích dẫn nguồn bằng ký hiệu [S1], [S2], v.v. "
            "Không bịa đặt thông tin ngoài nguồn đã cung cấp."
        )
        intent_suffixes: dict[str, str] = {
            "factual": " Trả lời ngắn gọn, thực tế, đúng trọng tâm.",
            "timeline": (
                " Sắp xếp theo thứ tự thời gian, dùng danh sách đánh số hoặc dấu gạch đầu dòng."
            ),
            "compare": (
                " So sánh rõ ràng theo từng khía cạnh (ví dụ: bối cảnh, quy mô, kết quả). "
                "Dùng bảng hoặc đoạn văn song song."
            ),
            "cause_effect": (
                " Phân tích nguyên nhân gốc rễ và hệ quả theo cấu trúc: "
                "1) Nguyên nhân, 2) Diễn biến, 3) Hệ quả trực tiếp, 4) Hệ quả lâu dài."
            ),
            "summary": (
                " Tóm tắt có cấu trúc: Tổng quan → Diễn biến chính → Kết quả → Ý nghĩa lịch sử."
            ),
            "source_audit": (
                " Liệt kê và đánh giá từng nguồn: tên, nội dung chính, mức độ liên quan."
            ),
            "multi_hop": (
                " Suy luận theo nhiều bước, kết nối các sự kiện và nhân vật liên quan; "
                "trình bày chuỗi lập luận rõ ràng."
            ),
            "source_check": (
                " Kiểm tra và xác minh từng tuyên bố dựa trên nguồn đã cung cấp; "
                "nêu rõ nguồn nào hỗ trợ hoặc mâu thuẫn."
            ),
        }
        return base + intent_suffixes.get(intent, "")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _flatten(value: Any, max_chars: int = 400) -> str:
    """Convert list or string value to a readable string."""
    if isinstance(value, list):
        joined = "; ".join(str(v) for v in value)
    else:
        joined = str(value)
    if len(joined) > max_chars:
        return joined[:max_chars].rstrip() + "..."
    return joined


def _str_trunc(value: Any, max_chars: int = 300) -> str:
    s = str(value)
    if len(s) > max_chars:
        return s[:max_chars].rstrip() + "..."
    return s
