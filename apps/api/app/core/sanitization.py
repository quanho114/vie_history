"""Input sanitization utilities for XSS and injection prevention."""

from __future__ import annotations

import html
import re
import shlex


def sanitize_html(text: str) -> str:
    """Sanitize HTML to prevent XSS attacks."""
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'\bon\w+\s*=\s*["\'].*?["\']', '', text, flags=re.IGNORECASE)
    text = re.sub(r'javascript:', '', text, flags=re.IGNORECASE)
    text = re.sub(r'data:text/html', '', text, flags=re.IGNORECASE)
    text = re.sub(r'<iframe[^>]*>.*?</iframe>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<object[^>]*>.*?</object>', '', text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r'<embed[^>]*>', '', text, flags=re.IGNORECASE)
    text = html.escape(text)
    return text


def sanitize_shell_arg(text: str) -> str:
    """Sanitize a string intended for shell argument use."""
    return shlex.quote(str(text))


def strip_html_tags(text: str) -> str:
    """Remove all HTML tags from text."""
    return re.sub(r'<[^>]+>', '', text)


def sanitize_filename(text: str) -> str:
    """Sanitize a string to be safe as a filename."""
    text = re.sub(r'[^\w\s\-_.]', '', text)
    text = re.sub(r'[\s]+', '_', text.strip())
    return text[:255]


def truncate_text(text: str, max_length: int = 10000) -> str:
    """Truncate text to a maximum length."""
    return text[:max_length] if text else ""
