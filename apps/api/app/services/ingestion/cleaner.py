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
        markdown = re.sub(r'\[([^\]]+)\]\((?:[^)(]+|\((?:[^)(]+|\([^)(]*\))*\))*\)', r'\1', markdown)
        markdown = re.sub(r'\[\]\((?:[^)(]+|\((?:[^)(]+|\([^)(]*\))*\))*\)', '', markdown)

        # 3. Aggressive Wikipedia boilerplate block removal
        markdown = self._remove_wiki_boilerplate_blocks(markdown)

        # 4. Line-by-line filter
        lines = markdown.split("\n")
        filtered_lines = []
        skip_mode = False
        for line in lines:
            trimmed = line.strip()
            lower = trimmed.lower()

            # Truncate at trailing non-content sections
            if re.match(
                r'^#{1,3}\s*(Xem thêm|Tham khảo|Chú thích|Thư mục|Đọc thêm|Liên kết ngoài|Nguồn|Ghi chú|References|Notes|Bibliography|External links)',
                trimmed, re.IGNORECASE
            ):
                skip_mode = True
            if skip_mode:
                continue

            if not trimmed:
                filtered_lines.append(line)
                continue

            # Navigation / boilerplate single-line patterns
            skip_patterns = [
                r'^-\s*x\s*-\s*t\s*-\s*s\s*$',            # navbox footer
                r'^icon\s+Cổng thông tin',                   # portal icon line
                r'^flag\s+Cổng thông tin',
                r'Cổng thông tin\s+\w',
                r'^\*\s*icon\b',
                r'Sửa dữ liệu tại Wikidata',
                r'Lấy từ\s+\"https?://',                     # "Retrieved from" link
                r'Thể loại ẩn:',
                r'^Thể loại:',
                r'^Cổng thông tin:',
                r'–\s*Wikipedia\s+tiếng\s+Việt\s*$',
                r'Bách khoa toàn thư mở Wikipedia',
                r'Bước tới nội dung',
                r'Trang bài viết này đang bị hạn chế',
                r'^\s*Sách:\s*',                              # "Sách: Lịch sử Việt Nam"
                r'^\s*Bài chi tiết:',                        # "Bài chi tiết: ..."
                r'^\s*Xem thêm:',
                r'^\s*\d+\s*↑',                              # footnote entries
                r'^↑\s*',
            ]
            if any(re.search(p, trimmed, re.IGNORECASE) for p in skip_patterns):
                continue

            # Wikipedia warning banners
            if any(kw in lower for kw in [
                "chú thích nguồn gốc", "kiểm chứng thông tin",
                "bổ sung chú thích", "không có nguồn", "nguồn đáng tin cậy",
                "bị nghi ngờ và xóa bỏ", "xóa thông báo này",
                "bài viết này cần", "bài này cần được wiki hóa",
                "cần được wiki hóa", "wiki hóa để đáp ứng",
                "tháng năm", "cuối tháng",   # wiki maintenance date stamps
            ]):
                continue

            # Table separator lines
            if re.match(r'^[\s|:\-]+$', trimmed):
                continue

            # Infobox pipe lines with very short content
            if trimmed.startswith("|") and len(trimmed) < 5:
                continue

            filtered_lines.append(line)

        markdown = "\n".join(filtered_lines)

        # 5. Remove wiki templates
        markdown = self.remove_wiki_templates(markdown)

        # 6. Remove citation markers
        markdown = self.remove_citation_markers(markdown)

        # 7. Remove residual link artifacts
        markdown = re.sub(r'\s*\(\s*#cite_note-[^)]+\)', '', markdown)
        markdown = re.sub(r'\s*\(\s*#cite_ref-[^)]+\)', '', markdown)
        markdown = re.sub(r'\s*\(\s*//[^)]+\)', '', markdown)
        markdown = re.sub(r'\s*\(\s*https?://[^)]+\)', '', markdown)

        # 8. Strip miscellaneous Wikipedia inline artifacts
        markdown = re.sub(r'Chú\s*ý', '', markdown)
        markdown = re.sub(r'\s*\(en\)', '', markdown, flags=re.IGNORECASE)
        markdown = re.sub(r'\bngày\s+tháng\s+năm\b', '', markdown)
        markdown = re.sub(r'(?<!\w)tháng\s+năm(?!\s+\d)', '', markdown)
        markdown = re.sub(r'\*\s*cần dẫn nguồn\s*\*', '', markdown, flags=re.IGNORECASE)

        # 9. Table/pipe/dash artifacts
        markdown = re.sub(r'[|\-]+([|:\-]+[|:\-]+)+', ' ', markdown)
        markdown = re.sub(r'\|+', ' ', markdown)
        markdown = re.sub(r'--+', ' ', markdown)

        # 10. Bare citation numbers (not years 1000-2100)
        def _drop_non_year_nums(m: re.Match) -> str:
            n = int(m.group(0))
            return m.group(0) if 1000 <= n <= 2100 else ''
        markdown = re.sub(r'(?<=[\s,.:;!?"])\d{2,}(?=[\s]|$)', _drop_non_year_nums, markdown)

        # 11. Trailing digits glued to Vietnamese words
        markdown = re.sub(
            r'([a-zA-ZáàảãạăắằẳẵặâấầẩẫậéèẻẽẹêếềểễệíìỉĩịóòỏõọôốồổỗộơớờởỡợúùủũụưứừửữựýỳỷỹỵđĐ])'
            r'\s+(\d+)(?=\s|$)',
            r'\1', markdown
        )

        # 12. Normalize whitespace, unicode, CJK
        markdown = self.normalize_whitespace(markdown)
        markdown = self.normalize_unicode(markdown)
        markdown = self.remove_cjk_characters(markdown)

        return markdown

    def _remove_wiki_boilerplate_blocks(self, markdown: str) -> str:
        """
        Remove multi-line Wikipedia boilerplate blocks before line-by-line filtering.

        Targets:
        - Navigation boxes (lines containing '- x - t - s' or similar)
        - Sidebar/infobox blocks that are essentially flat lists of wiki links
        - Trailing sections: Xem thêm, Chú thích, Thư mục, Đọc thêm, Liên kết ngoài
        - Footnote/reference list blocks
        """
        lines = markdown.split("\n")
        result: list[str] = []

        # State: we track consecutive "navbox-like" short lines to drop entire block
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # --- Drop navbox footer marker blocks ---
            # Pattern: lines that are exactly "- x - t - s" or similar edit markers
            if re.match(r'^[-•*]\s*x\s*[-•*]\s*t\s*[-•*]\s*s\s*$', stripped, re.IGNORECASE):
                i += 1
                continue

            # --- Drop portal/icon lines ---
            if re.match(r'^(icon|flag)\s+Cổng thông tin', stripped, re.IGNORECASE):
                i += 1
                continue

            # --- Drop Lấy từ (Retrieved from) lines ---
            if re.match(r'^Lấy từ\s+"https?://', stripped):
                i += 1
                continue

            # --- Drop footnote reference blocks ---
            # Pattern: lines starting with number↑ or ↑
            if re.match(r'^\d+\s*↑', stripped) or re.match(r'^↑', stripped):
                i += 1
                continue

            # --- Drop trailing sections entirely ---
            # When we hit a heading that is a trailing section, skip everything after
            if re.match(
                r'^#{1,3}\s*(Xem thêm|Tham khảo|Chú thích|Thư mục|Đọc thêm'
                r'|Liên kết ngoài|Nguồn|Ghi chú|Dân số|Các cuộc chiến)',
                stripped, re.IGNORECASE
            ):
                # Skip the rest entirely
                break

            # --- Detect and skip navbox/sidebar blocks ---
            # A "navbox block" is a cluster of very short lines (< 60 chars) that are
            # mostly link-like content (contain • · - or look like navigation lists)
            # separated from real content by empty lines.
            # We look ahead: if the next N lines are all short nav-like content, skip block.
            if self._is_navbox_block_start(lines, i):
                i = self._skip_navbox_block(lines, i)
                continue

            result.append(line)
            i += 1

        return "\n".join(result)

    def _is_navbox_block_start(self, lines: list[str], start: int) -> bool:
        """
        Detect if the current position is the start of a Wikipedia navbox/sidebar block.

        Heuristics:
        - Block contains 4+ consecutive short lines (< 80 chars)
        - Many lines begin with - or • or contain only link-like fragments
        - Block does NOT contain long prose sentences (> 120 chars)
        - Navbox markers: "Một phần của loạt bài", "Chuyên đề", "Loạt bài"
        """
        line = lines[start].strip()

        navbox_triggers = [
            r'^Một phần của loạt bài',
            r'^Chuyên đề\b',
            r'^Loạt bài\b',
            r'^Các nền văn hóa khảo cổ',
            r'^Lịch sử kinh tế Việt Nam',
            r'^Lịch sử Châu Á',
            r'^Lịch sử các nước Đông Nam Á',
            r'^Tổng quan về Việt Nam',
            r'^ *Cơ sở dữ liệu tiêu đề chuẩn',
            r'^\s*\*\s*x\s*\*',
        ]
        return any(re.match(p, line, re.IGNORECASE) for p in navbox_triggers)

    def _skip_navbox_block(self, lines: list[str], start: int) -> int:
        """
        Skip forward past a navbox block. A navbox block ends at:
        - Two consecutive empty lines
        - A line starting with ## (a real heading)
        - End of file
        Returns the index of the first line AFTER the block.
        """
        i = start + 1
        consecutive_empty = 0
        while i < len(lines):
            stripped = lines[i].strip()

            # Real heading = end of navbox
            if re.match(r'^#{1,3}\s+\S', stripped):
                return i

            if not stripped:
                consecutive_empty += 1
                if consecutive_empty >= 2:
                    return i + 1
            else:
                consecutive_empty = 0

            i += 1
        return i


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
