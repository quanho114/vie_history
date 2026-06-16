"""Response Builder service."""

from typing import Any

from app.core.logging import get_logger

logger = get_logger("response_builder")


class ResponseBuilder:
    """
    Builds structured responses with citations and traces.
    """

    def build_factual(
        self,
        answer: str,
        chunks: list[dict],
        trace: dict,
    ) -> dict:
        """Build factual response."""
        return {
            "answer": answer,
            "citations": self._build_citations(chunks),
            "mode": "factual",
            "trace": trace,
        }

    def build_timeline(
        self,
        events: list[dict],
        chunks: list[dict],
        trace: dict,
    ) -> dict:
        """Build timeline response."""
        timeline_markdown = self._build_timeline_markdown(events)

        return {
            "answer": timeline_markdown,
            "timeline_events": events,
            "citations": self._build_citations(chunks),
            "mode": "timeline",
            "trace": trace,
        }

    def build_compare(
        self,
        comparison: dict,
        chunks_a: list[dict],
        chunks_b: list[dict],
        trace: dict,
    ) -> dict:
        """Build comparison response."""
        return {
            "answer": self._build_compare_markdown(comparison),
            "comparison": comparison,
            "citations": self._build_citations(chunks_a + chunks_b),
            "mode": "compare",
            "trace": trace,
        }

    def build_summary(
        self,
        summary: str,
        chunks: list[dict],
        trace: dict,
    ) -> dict:
        """Build summary response."""
        return {
            "answer": summary,
            "citations": self._build_citations(chunks),
            "mode": "summary",
            "trace": trace,
        }

    def build_source_audit(
        self,
        sources: list[dict],
        chunks: list[dict],
        trace: dict,
    ) -> dict:
        """Build source audit response."""
        return {
            "answer": self._build_source_list_markdown(sources),
            "sources": sources,
            "citations": self._build_citations(chunks),
            "mode": "source_audit",
            "trace": trace,
        }

    def build_out_of_scope(self, query: str, trace: dict) -> dict:
        """Build out-of-scope response."""
        return {
            "answer": (
                f"Query '{query}' is outside the scope of this system. "
                "This AI research agent focuses on Vietnamese history from 1945-1975."
            ),
            "citations": [],
            "mode": "out_of_scope",
            "trace": trace,
        }

    def _build_citations(self, chunks: list[dict]) -> list[dict]:
        """Build citation list from chunks."""
        citations = []
        for chunk in chunks:
            citations.append({
                "document_id": str(chunk.get("document_id") or ""),
                "document_title": chunk.get("document_title", "Unknown"),
                "source_url": chunk.get("source_url"),
                "chunk_id": str(chunk.get("chunk_id") or ""),
                "section_title": chunk.get("section_title"),
                "excerpt": self._build_excerpt(chunk.get("content", "")),
                "score": chunk.get("score", 0.0),
            })
        return citations

    def _build_excerpt(self, content: str) -> str:
        """Build a compact citation excerpt."""
        compact = " ".join(content.split())
        if len(compact) <= 300:
            return compact
        return compact[:299].rstrip() + "..."

    def _build_timeline_markdown(self, events: list[dict]) -> str:
        """Build markdown timeline."""
        lines = ["## Timeline\n"]
        for event in events:
            year = event.get("year", "?")
            title = event.get("title", "Event")
            description = event.get("description", "")

            lines.append(f"### {year}: {title}")
            if description:
                lines.append(f"{description}\n")
            lines.append("")

        return "\n".join(lines)

    def _build_compare_markdown(self, comparison: dict) -> str:
        """Build markdown comparison table."""
        lines = ["## Comparison\n"]

        subjects = comparison.get("subjects", [])
        aspects = comparison.get("aspects", {})

        if not aspects:
            return "Comparison data not available."

        # Build table header
        lines.append("| Aspect | " + " | ".join(subjects) + " |")
        lines.append("|" + "|".join(["---"] * (len(subjects) + 1)) + "|")

        for aspect, values in aspects.items():
            cells = [aspect]
            for subject in subjects:
                cells.append(values.get(subject, "N/A"))
            lines.append("| " + " | ".join(cells) + " |")

        return "\n".join(lines)

    def _build_source_list_markdown(self, sources: list[dict]) -> str:
        """Build markdown source list."""
        lines = ["## Sources\n"]
        for i, source in enumerate(sources, 1):
            title = source.get("title", "Unknown")
            url = source.get("url", "")
            relevance = source.get("relevance", 0.0)

            lines.append(f"### {i}. {title}")
            lines.append(f"**Relevance:** {relevance:.2f}")
            if url:
                lines.append(f"**URL:** {url}")
            lines.append("")

        return "\n".join(lines)
