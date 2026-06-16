"""Grounded answer synthesis with citation validation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("answer_synthesizer")

SOURCE_MARKER_RE = re.compile(r"\[S\d+\]")


@dataclass
class SynthesisResult:
    """Answer synthesis result."""

    answer: str
    used_llm: bool
    validation_passed: bool
    failure_reason: str | None = None


class AnswerSynthesizer:
    """Generate grounded Vietnamese answers with strict citation markers."""

    async def synthesize(
        self,
        query: str,
        intent: str,
        chunks: list[dict[str, Any]],
        verification_message: str | None = None,
        system_prompt: str | None = None,
        user_prompt: str | None = None,
    ) -> SynthesisResult:
        """Synthesize an answer from chunks."""
        if not chunks:
            return SynthesisResult(
                answer=(
                    "Mình chưa tìm thấy đủ tư liệu đã được lập chỉ mục để trả lời câu hỏi này. "
                    "Bạn có thể nhập thêm tài liệu nguồn hoặc thử hỏi hẹp hơn theo nhân vật, "
                    "sự kiện, địa danh hoặc mốc năm cụ thể."
                ),
                used_llm=False,
                validation_passed=True,
            )

        llm_answer = await self._try_llm(
            query=query,
            intent=intent,
            chunks=chunks,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        if llm_answer:
            try:
                from app.services.citation.verifier import CitationVerifier
                verifier = CitationVerifier()
                verification = await verifier.verify(llm_answer, chunks)
                verified_answer = verification["verified_answer"]
                validation = self._validate_answer(verified_answer)
                if validation is None:
                    return SynthesisResult(
                        answer=verified_answer,
                        used_llm=True,
                        validation_passed=True,
                    )
                logger.warning("llm_answer_failed_citation_validation", reason=validation)
            except Exception as exc:
                logger.error("citation_verification_failed_falling_back", error=str(exc))
                validation = self._validate_answer(llm_answer)
                if validation is None:
                    return SynthesisResult(
                        answer=llm_answer,
                        used_llm=True,
                        validation_passed=True,
                    )
                logger.warning("llm_answer_failed_citation_validation", reason=validation)

        return SynthesisResult(
            answer=self._build_extractive_answer(
                query=query,
                intent=intent,
                chunks=chunks,
                verification_message=verification_message,
            ),
            used_llm=False,
            validation_passed=llm_answer is None,
            failure_reason="llm_unavailable_or_failed_citation_validation" if llm_answer else None,
        )

    async def _try_llm(
        self,
        query: str,
        intent: str,
        chunks: list[dict[str, Any]],
        system_prompt: str | None = None,
        user_prompt: str | None = None,
    ) -> str | None:
        if settings.APP_ENV == "testing":
            return None

        try:
            from app.services.llm.client import get_llm_client
            client = get_llm_client()
            prompt = user_prompt or self._build_prompt(query=query, intent=intent, chunks=chunks)
            system = system_prompt or self._system_prompt()
            return await client.generate(prompt, system=system, max_tokens=1200)
        except Exception as exc:
            logger.error("llm_synthesis_failed_propagating", error=str(exc))
            raise exc

    def _system_prompt(self) -> str:
        return (
            "Bạn là HistoriAI, trợ lý nghiên cứu lịch sử Việt Nam chuyên nghiệp.\n"
            "1. Chỉ dùng thông tin trong SOURCES. Mỗi câu có thông tin lịch sử cụ thể bắt buộc kết thúc bằng citation dạng [S1], [S2].\n"
            "2. XỬ LÝ MÂU THUẪN SỬ LIỆU (Conflict Resolution): Nếu các nguồn tài liệu có ghi chép mâu thuẫn về số lượng quân, ngày tháng, diễn biến hoặc địa điểm (ví dụ: Nguồn [S1] ghi nhận 20 vạn quân, Nguồn [S2] ghi nhận 29 vạn quân), bạn BẮT BUỘC phải chỉ rõ sự mâu thuẫn này một cách khách quan. Sử dụng định dạng so sánh đối chiếu rõ ràng: 'Có sự mâu thuẫn giữa các nguồn: [S1] ghi là... trong khi [S2] ghi là...'.\n"
            "3. Không tự ý bịa đặt tên, ngày, số liệu hoặc diễn giải ngoài nguồn.\n"
            "4. ĐỘ DÀI & PHONG CÁCH TRÌNH BÀY (Conciseness & Formatting):\n"
            "   - Hãy viết cực kỳ súc tích, đi thẳng vào câu trả lời, tuyệt đối không viết các câu dẫn dài dòng, mở bài/kết bài sáo rỗng hoặc diễn giải dư thừa.\n"
            "   - Sử dụng các tiêu đề ngắn (Headers), danh sách gạch đầu dòng (bullets) hoặc danh sách số thứ tự (ordered lists) để cấu trúc thông tin rõ ràng, dễ theo dõi.\n"
            "   - In đậm (**bằng cú pháp markdown**) các mốc thời gian quan trọng, ngày tháng, tên nhân vật lịch sử, địa danh hoặc thuật ngữ chính để nhấn mạnh trực quan trên giao diện."
        )

    def _build_prompt(self, query: str, intent: str, chunks: list[dict[str, Any]]) -> str:
        source_blocks = []
        for index, chunk in enumerate(chunks[:8], 1):
            title = chunk.get("document_title") or "Nguồn chưa đặt tên"
            section = chunk.get("section_title") or ""
            content = self._clean_chunk_text(chunk.get("content", ""))[:1800]
            source_blocks.append(f"[S{index}] {title} {section}\n{content}")

        return (
            f"QUERY: {query}\n"
            f"INTENT: {intent}\n\n"
            "SOURCES:\n"
            + "\n\n".join(source_blocks)
            + "\n\nTrả lời bằng tiếng Việt, súc tích, học thuật, có citation ở từng câu có claim."
        )

    def _validate_answer(self, answer: str) -> str | None:
        clean_lines = [line.strip() for line in answer.splitlines() if line.strip()]
        claim_lines = [
            line
            for line in clean_lines
            if not line.startswith(("#", "-", "*")) and len(line) >= 40
        ]
        if not claim_lines:
            return "answer_has_no_claim_lines"
        missing = [line for line in claim_lines if not SOURCE_MARKER_RE.search(line)]
        if missing:
            return "claim_without_source_marker"
        return None

    def _build_extractive_answer(
        self,
        query: str,
        intent: str,
        chunks: list[dict[str, Any]],
        verification_message: str | None,
    ) -> str:
        intro = {
            "timeline": "Dựa trên các tư liệu tìm được, có thể dựng lại các ý chính theo trình tự sau:",
            "compare": "Dựa trên các tư liệu tìm được, các điểm so sánh chính là:",
            "summary": "Dựa trên các tư liệu tìm được, tóm tắt ngắn gọn như sau:",
            "source_audit": "Các nguồn liên quan nhất hiện có trong hệ thống là:",
        }.get(intent, "Dựa trên các tư liệu tìm được, câu trả lời có thể tóm lược như sau:")

        lines = [intro, ""]
        for index, chunk in enumerate(chunks[:5], 1):
            excerpt = self._compact_excerpt(self._clean_chunk_text(chunk.get("content", "")))
            lines.append(f"{index}. {excerpt} [S{index}]")

        if verification_message:
            lines.extend(["", f"Lưu ý kiểm chứng: {verification_message}"])

        lines.extend(
            [
                "",
                "Phần trên chỉ sử dụng nội dung đã lập chỉ mục; các kết luận không có nguồn đã được loại bỏ.",
            ]
        )
        return "\n".join(lines)

    def _compact_excerpt(self, text: str, max_chars: int = 420) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= max_chars:
            return normalized
        return normalized[: max_chars - 1].rstrip() + "..."

    # ------------------------------------------------------------------
    # Runtime chunk cleaning (for already-indexed documents)
    # ------------------------------------------------------------------

    _WIKI_PIPE_RE = re.compile(r"[|\-]+([|:\-]+[|:\-]+)+")
    _PIPE_RE = re.compile(r"\|+")
    _DOUBLE_DASH_RE = re.compile(r"--+")
    _WIKI_TITLE_RE = re.compile(r"\u2013\s*Wikipedia\s+ti\u1ebfng\s+Vi\u1ec7t\s*$")
    _BLANK_DATE_RE = re.compile(r"\bng\u00e0y\s+th\u00e1ng\s+n\u0103m\b")
    _BARE_MONTH_RE = re.compile(r"(?<!\w)th\u00e1ng\s+n\u0103m(?!\s+\d)")
    _CIT_NUM_RE = re.compile(r"(?<=[\s,.:;!?])\d{2,}(?=[\s]|$)")

    _WARN_KEYWORDS = (
        "ch\u00fa th\u00edch ngu\u1ed3n g\u1ed1c",
        "ki\u1ec3m ch\u1ee9ng th\u00f4ng tin",
        "b\u1ed5 sung ch\u00fa th\u00edch",
        "kh\u00f4ng c\u00f3 ngu\u1ed3n",
        "ngu\u1ed3n \u0111\u00e1ng tin c\u1eady",
        "b\u1ecb nghi ng\u1edd v\u00e0 x\u00f3a b\u1ecf",
        "x\u00f3a th\u00f4ng b\u00e1o n\u00e0y",
        "b\u00e0i vi\u1ebft n\u00e0y c\u1ea7n",
        "t\u00ecm hi\u1ec3u c\u00e1ch th\u1ee9c",
    )

    def _clean_chunk_text(self, text: str) -> str:
        """Strip Wikipedia formatting artifacts from a stored chunk at query time."""
        if not text:
            return text

        # Process line by line first
        clean_lines: list[str] = []
        for line in text.splitlines():
            t = line.strip()
            lo = t.lower()
            # Drop pure table separator lines
            if re.match(r"^[\s|:\-]+$", t):
                continue
            # Drop Wikipedia warning banners
            if any(kw in lo for kw in self._WARN_KEYWORDS):
                continue
            # Drop Wikipedia page title lines
            if self._WIKI_TITLE_RE.search(t):
                continue
            # Drop category / portal lines
            if t.startswith(("Th\u1ec3 lo\u1ea1i:", "C\u1ed5ng th\u00f4ng tin:")):
                continue
            clean_lines.append(line)

        cleaned = "\n".join(clean_lines)

        # Inline substitutions
        cleaned = re.sub(r"Ch\u00fa\s*\u00fd", "", cleaned)          # "Chu y"
        cleaned = re.sub(r"\s*\(en\)", "", cleaned, flags=re.IGNORECASE)
        cleaned = self._BLANK_DATE_RE.sub("", cleaned)
        cleaned = self._BARE_MONTH_RE.sub("", cleaned)
        cleaned = self._WIKI_PIPE_RE.sub(" ", cleaned)
        cleaned = self._PIPE_RE.sub(" ", cleaned)
        cleaned = self._DOUBLE_DASH_RE.sub(" ", cleaned)

        def _drop_non_year(m: re.Match) -> str:
            n = int(m.group(0))
            return m.group(0) if 1000 <= n <= 2100 else ""

        cleaned = self._CIT_NUM_RE.sub(_drop_non_year, cleaned)

        # Collapse extra whitespace
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()
