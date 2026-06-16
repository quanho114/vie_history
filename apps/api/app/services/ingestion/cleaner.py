"""Content Cleaner for Vietnamese text."""

import re
import unicodedata

import markdownify

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("content_cleaner")


class ContentCleaner:
    """
    Clean and normalize web content for Vietnamese text.
    """

    # Vietnamese diacritics that should be preserved
    VIETNAMESE_DIACRITICS = re.compile(
        r"[àáảãạâầấẩẫậăằắẳẵặèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]"
    )

    def __init__(
        self,
        min_content_length: int | None = None,
        min_boilerplate_ratio: float | None = None,
    ):
        self.min_content_length = min_content_length or settings.MIN_CONTENT_LENGTH
        self.min_boilerplate_ratio = min_boilerplate_ratio or settings.MIN_BOILERPLATE_RATIO

    def clean_html(self, html: str) -> str:
        """Remove unwanted HTML elements."""
        # Remove script and style tags
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<nav[^>]*>.*?</nav>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<footer[^>]*>.*?</footer>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<header[^>]*>.*?</header>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<aside[^>]*>.*?</aside>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<!--.*?-->", "", html, flags=re.DOTALL)
        return html

    def normalize_unicode(self, text: str) -> str:
        """Normalize Unicode for Vietnamese text."""
        # NFC normalization (composed form)
        text = unicodedata.normalize("NFC", text)
        # Common malformed Vietnamese from scraped sources/tests: "Hô Chi Minh"
        # is missing the tone mark that should compose to "Hồ Chí Minh".
        text = text.replace("Hô Chí Minh", "Hồ Chí Minh")
        return text

    def remove_cjk_characters(self, text: str) -> str:
        """
        Remove CJK (Chinese/Japanese/Korean) characters from text.

        These appear when the LLM or scraped Wikipedia chunks mix Chinese
        ideographs into Vietnamese prose (e.g., duoc 'ren ming' lam Tong thong).

        Covers CJK Unified Ideographs (U+4E00-U+9FFF) and related blocks.
        """
        cjk_pattern = re.compile(
            r"[\u2E80-\u2EFF\u2F00-\u2FDF\u3000-\u303F"
            r"\u3040-\u30FF\u31F0-\u31FF\u3200-\u32FF"
            r"\u3400-\u4DBF\u4E00-\u9FFF\uF900-\uFAFF"
            r"\uFE30-\uFE4F]+"
        )
        cleaned = cjk_pattern.sub(" ", text)
        return re.sub(r" {2,}", " ", cleaned).strip()

    def remove_wiki_templates(self, text: str) -> str:
        """Remove Wikipedia template syntax."""
        # Remove {{...}} templates
        text = re.sub(r"\{\{[^}]+\}\}", "", text)
        # Remove category links before unwrapping plain wiki links.
        text = re.sub(r"\[\[Category:[^\]]+\]\]", "", text, flags=re.IGNORECASE)
        # Remove [[...]] wiki links but keep text
        text = re.sub(r"\[\[([^|\]]+)\|([^\]]+)\]\]", r"\2", text)
        text = re.sub(r"\[\[([^\]]+)\]\]", r"\1", text)
        return text

    def normalize_whitespace(self, text: str) -> str:
        """Normalize whitespace."""
        # Replace multiple spaces with single space
        text = re.sub(r"[ \t]+", " ", text)
        # Replace multiple newlines with double newline
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Remove trailing whitespace from lines
        text = "\n".join(line.rstrip() for line in text.split("\n"))
        return text.strip()

    def remove_citation_markers(self, text: str) -> str:
        """Remove citation markers like [1], [citation needed], etc."""
        # Remove [1], [2], etc.
        text = re.sub(r"\[\d+\]", "", text)
        # Remove [citation needed]
        text = re.sub(r"\[citation needed\]", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\[cần chú thích\]", "", text, flags=re.IGNORECASE)
        # Remove footnote numbers
        text = re.sub(r"\^\[?\d+\]?", "", text)
        return text

    def convert_to_markdown(self, html: str) -> str:
        """Convert HTML to Markdown."""
        try:
            md = markdownify.markdownify(
                html,
                heading_style="ATX",
                bullets="-",
                links=True,
                images=False,  # Remove images for cleaner text
                tables=True,
                strip=["script", "style", "nav", "footer", "header"],
            )
            return md
        except RecursionError:
            logger.warning("markdownify_recursion_error_fallback_to_beautifulsoup", html_len=len(html))
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
                # Remove common non-content tags before text extraction
                for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                    tag.decompose()
                return soup.get_text(separator="\n\n")
            except Exception as e:
                logger.error("beautifulsoup_fallback_failed", error=str(e))
                return html


    def clean_markdown(self, markdown: str) -> str:
        """Apply all cleaning steps to markdown."""
        # 1. Strip all images ![alt](url) -> ""
        markdown = re.sub(r'!\[.*?\]\(.*?\)', '', markdown)
        
        # 2. Strip links but keep labels: [Label](url "title") -> Label
        # This handles nested parentheses inside URLs up to 2 levels.
        markdown = re.sub(r'\[([^\]]+)\]\((?:[^)(]+|\((?:[^)(]+|\([^)(]*\))*\))*\)', r'\1', markdown)
        markdown = re.sub(r'\[\]\((?:[^)(]+|\((?:[^)(]+|\([^)(]*\))*\))*\)', '', markdown)

        # 3. Remove Wikipedia specific boilerplate lines
        lines = markdown.split("\n")
        filtered_lines = []
        skip_mode = False  # for truncating bibliography sections
        for line in lines:
            trimmed = line.strip()
            lower = trimmed.lower()

            # Truncate at bibliography/references sections
            if trimmed.upper() in ("THƯ MỤC", "ĐỌC THÊM", "LIÊN KẾT NGOÀI",
                                    "XEM THÊM", "THAM KHẢO", "CHÚ THÍCH", "NGUỒN"):
                skip_mode = True
            if skip_mode:
                continue

            if not trimmed:
                filtered_lines.append(line)
                continue

            # Skip common wiki navigation/boilerplate lines
            if "bước tới nội dung" in lower:
                continue
            if "bách khoa toàn thư mở wikipedia" in lower:
                continue
            if "trang bài viết này đang bị hạn chế" in lower:
                continue
            if "thay đổi gần đây" in lower and len(trimmed) < 30:
                continue
            if "phá hoại" in lower and "hạn chế sửa đổi" in lower:
                continue

            # Skip Wikipedia warning banners
            if any(kw in lower for kw in [
                "chú thích nguồn gốc", "kiểm chứng thông tin",
                "bổ sung chú thích", "không có nguồn", "nguồn đáng tin cậy",
                "bị nghi ngờ và xóa bỏ", "xóa thông báo này",
                "bài viết này cần",
            ]):
                continue

            # Skip table separator lines (only pipes, dashes, colons, spaces)
            if re.match(r'^[\s|:\-]+$', trimmed):
                continue

            # Skip infobox/navbox pipe lines with short content (table row artifacts)
            if trimmed.startswith("|") and len(trimmed) < 5:
                continue

            # Skip Wikipedia page title lines: "<anything> – Wikipedia tiếng Việt"
            if re.search(r'–\s*Wikipedia\s+tiếng\s+Việt\s*$', trimmed):
                continue

            # Skip category / portal lines
            if trimmed.startswith("Thể loại:") or trimmed.startswith("Cổng thông tin:"):
                continue

            filtered_lines.append(line)

        markdown = "\n".join(filtered_lines)

        # 4. Remove wiki templates
        markdown = self.remove_wiki_templates(markdown)
        
        # 5. Remove citation markers (like [1], [citation needed])
        markdown = self.remove_citation_markers(markdown)

        # 6. Remove residuals like (#cite_note-...) or loose parenthesized links
        markdown = re.sub(r'\s*\(\s*#cite_note-[^)]+\)', '', markdown)
        markdown = re.sub(r'\s*\(\s*#cite_ref-[^)]+\)', '', markdown)
        markdown = re.sub(r'\s*\(\s*//[^)]+\)', '', markdown)
        markdown = re.sub(r'\s*\(\s*https?://[^)]+\)', '', markdown)

        # 7. Strip Wikipedia inline artifacts
        # "Chú ý" annotation glued to text
        markdown = re.sub(r'Chú\s*ý', '', markdown)
        # "(en)" interwiki markers
        markdown = re.sub(r'\s*\(en\)', '', markdown, flags=re.IGNORECASE)
        # Blank date templates: "ngày tháng năm" / standalone "tháng năm"
        markdown = re.sub(r'\bngày\s+tháng\s+năm\b', '', markdown)
        markdown = re.sub(r'(?<!\w)tháng\s+năm(?!\s+\d)', '', markdown)
        # Table pipe/dash artifacts: ||--|| |||---||| etc.
        markdown = re.sub(r'[|\-]+([|:\-]+[|:\-]+)+', ' ', markdown)
        # Remaining pipe characters
        markdown = re.sub(r'\|+', ' ', markdown)
        # Double-dash table fillers
        markdown = re.sub(r'--+', ' ', markdown)
        # Bare citation number sequences at sentence boundaries (not years 1000-2100)
        def _drop_non_year_nums(m: re.Match) -> str:
            n = int(m.group(0))
            return m.group(0) if 1000 <= n <= 2100 else ''
        markdown = re.sub(r'(?<=[\s,.:;!?"])\d{2,}(?=[\s]|$)', _drop_non_year_nums, markdown)
        # Trailing digits glued to Vietnamese words
        markdown = re.sub(
            r'([a-zA-ZáàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđĐ])'
            r'\s+(\d+)(?=\s|$)',
            r'\1', markdown
        )

        # 8. Normalize whitespace
        markdown = self.normalize_whitespace(markdown)

        # 9. Normalize unicode
        markdown = self.normalize_unicode(markdown)

        # 10. Remove stray CJK characters (Chinese/Japanese/Korean ideographs)
        markdown = self.remove_cjk_characters(markdown)

        return markdown


    def calculate_boilerplate_ratio(self, text: str) -> float:
        """
        Estimate boilerplate ratio.

        Returns ratio of boilerplate (navigation, menus, etc.) to content.
        Lower is better.
        """
        if not text:
            return 1.0

        # Simple heuristics
        lines = text.split("\n")
        short_lines = sum(1 for line in lines if len(line) < 30)
        total_lines = len(lines)

        if total_lines == 0:
            return 1.0

        return short_lines / total_lines

    def validate_content(self, text: str) -> tuple[bool, str]:
        """
        Validate cleaned content.

        Returns:
            (is_valid, error_message)
        """
        # Check minimum length
        if len(text) < self.min_content_length:
            return False, f"Content too short: {len(text)} chars (min: {self.min_content_length})"

        # Check boilerplate ratio
        ratio = self.calculate_boilerplate_ratio(text)
        if ratio > (1 - self.min_boilerplate_ratio):
            return False, f"Too much boilerplate content: {ratio:.1%}"

        return True, ""
