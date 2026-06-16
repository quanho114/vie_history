"""Unit tests for content cleaner."""

import pytest

from app.services.ingestion.cleaner import ContentCleaner


class TestCleanHTML:
    """HTML cleaning tests."""

    def test_removes_script_tags(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        html = "<script>alert('xss')</script><p>Content</p>"

        result = cleaner.clean_html(html)

        assert "alert" not in result
        assert "Content" in result

    def test_removes_style_tags(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        html = "<style>.hidden{display:none}</style><p>Content</p>"

        result = cleaner.clean_html(html)

        assert ".hidden" not in result
        assert "Content" in result

    def test_removes_nav_footer_header_aside(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        html = "<nav>NavMenu</nav><article><p>Main content</p></article><footer>Footer</footer>"

        result = cleaner.clean_html(html)

        assert "NavMenu" not in result
        assert "Footer" not in result
        assert "Main content" in result

    def test_removes_html_comments(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        html = "<!-- This is a comment --><p>Visible</p>"

        result = cleaner.clean_html(html)

        assert "comment" not in result
        assert "Visible" in result


class TestNormalizeUnicode:
    """Unicode normalization tests."""

    def test_nfc_normalization_preserves_diacritics(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        text = "Hồ Chí Minh"

        result = cleaner.normalize_unicode(text)

        assert "Hồ" in result
        assert "Minh" in result

    def test_composes_decomposed_vietnamese(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        # NFD form: H + combining acute accent
        decomposed = "Ho\u0302 Ch\u00ed Minh"

        result = cleaner.normalize_unicode(decomposed)

        assert "Hồ" in result


class TestRemoveWikiTemplates:
    """Wikipedia template removal tests."""

    def test_removes_double_brace_templates(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        text = "Start {{main|Article}} End"

        result = cleaner.remove_wiki_templates(text)

        assert "{{main" not in result
        assert "Start" in result
        assert "End" in result

    def test_removes_wiki_links_with_pipe(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        text = "See [[Vietnamese language|Vietnamese]] for more."

        result = cleaner.remove_wiki_templates(text)

        assert "Vietnamese language" not in result
        assert "Vietnamese" in result

    def test_removes_plain_wiki_links(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        text = "The [[Hồ Chí Minh]] was a leader."

        result = cleaner.remove_wiki_templates(text)

        assert "[[Hồ Chí Minh]]" not in result
        assert "Hồ Chí Minh" in result

    def test_removes_category_links(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        text = "Article [[Category:Vietnam history]] more text"

        result = cleaner.remove_wiki_templates(text)

        assert "Category:" not in result


class TestRemoveCitationMarkers:
    """Citation marker removal tests."""

    def test_removes_numeric_citations(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        text = "Some claim[1] and another[2] claim."

        result = cleaner.remove_citation_markers(text)

        assert "[1]" not in result
        assert "[2]" not in result
        assert "Some claim" in result

    def test_removes_citation_needed(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        text = "Fact [citation needed] more text"

        result = cleaner.remove_citation_markers(text)

        assert "[citation needed]" not in result
        assert "Fact" in result

    def test_removes_vietnamese_citation_needed(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        text = "Thông tin [cần chú thích] trong bài"

        result = cleaner.remove_citation_markers(text)

        assert "[cần chú thích]" not in result


class TestNormalizeWhitespace:
    """Whitespace normalization tests."""

    def test_collapses_multiple_spaces(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        text = "Multiple    spaces   here"

        result = cleaner.normalize_whitespace(text)

        assert "    " not in result
        assert "Multiple spaces here" in result

    def test_collapses_multiple_newlines(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        text = "Line 1\n\n\n\n\nLine 2"

        result = cleaner.normalize_whitespace(text)

        assert "\n\n\n\n" not in result
        assert "Line 1\n\nLine 2" in result

    def test_trims_leading_trailing_whitespace(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        text = "  \n  Content  \n  "

        result = cleaner.normalize_whitespace(text)

        assert result.startswith("Content")


class TestCalculateBoilerplateRatio:
    """Boilerplate ratio calculation tests."""

    def test_empty_text_returns_full_boilerplate(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)

        ratio = cleaner.calculate_boilerplate_ratio("")

        assert ratio == 1.0

    def test_mostly_short_lines_high_ratio(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        text = "Nav\nNav\nNav\nNav\nNav"

        ratio = cleaner.calculate_boilerplate_ratio(text)

        assert ratio > 0.8

    def test_long_content_lines_low_ratio(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        text = "This is a long sentence about Vietnamese history.\n" * 10

        ratio = cleaner.calculate_boilerplate_ratio(text)

        assert ratio < 0.5


class TestValidateContent:
    """Content validation tests."""

    def test_rejects_content_too_short(self) -> None:
        cleaner = ContentCleaner(min_content_length=500, min_boilerplate_ratio=0.3)
        text = "Short content."

        valid, error = cleaner.validate_content(text)

        assert valid is False
        assert "too short" in error

    def test_rejects_high_boilerplate(self) -> None:
        cleaner = ContentCleaner(min_content_length=10, min_boilerplate_ratio=0.5)
        text = "Nav\nNav\nNav\nNav\nNav\nNav\nNav\nNav\nNav\nNav"

        valid, error = cleaner.validate_content(text)

        assert valid is False
        assert "boilerplate" in error

    def test_accepts_valid_content(self) -> None:
        cleaner = ContentCleaner(min_content_length=50, min_boilerplate_ratio=0.3)
        text = "This is a well-formed paragraph about Vietnamese history with enough content to pass validation."

        valid, error = cleaner.validate_content(text)

        assert valid is True
        assert error == ""


class TestCleanMarkdown:
    """Full markdown cleaning pipeline tests."""

    def test_combined_cleaning_pipeline(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        markdown = (
            "{{ref|1}}\n"
            "  Multiple   spaces   here\n\n\n"
            "[[Vietnamese people|Vietnamese]] claim[1]\n"
        )

        result = cleaner.clean_markdown(markdown)

        assert "{{ref" not in result
        assert "[[" not in result
        assert "[1]" not in result
        assert "Multiple spaces here" in result


class TestRemoveCJKCharacters:
    """CJK character removal tests."""

    def test_removes_chinese_ideographs(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        text = "được 任命 làm Tổng thống"

        result = cleaner.remove_cjk_characters(text)

        assert "任命" not in result
        assert "được" in result
        assert "làm Tổng thống" in result

    def test_preserves_vietnamese_diacritics(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        text = "Hồ Chí Minh lãnh đạo cuộc kháng chiến"

        result = cleaner.remove_cjk_characters(text)

        assert result == text  # nothing should change

    def test_removes_multiple_cjk_blocks(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        text = "Sự kiện 任命 xảy ra vào 宣布 năm 1975"

        result = cleaner.remove_cjk_characters(text)

        assert "任命" not in result
        assert "宣布" not in result
        assert "1975" in result

    def test_empty_string_returns_empty(self) -> None:
        cleaner = ContentCleaner(min_content_length=0)
        assert cleaner.remove_cjk_characters("") == ""

    def test_clean_markdown_strips_cjk(self) -> None:
        """Integration: full clean_markdown pipeline removes CJK."""
        cleaner = ContentCleaner(min_content_length=0)
        text = "Tổng thống được 任命 bởi Quốc hội."

        result = cleaner.clean_markdown(text)

        assert "任命" not in result
        assert "Tổng thống" in result
