"""Content Extractor — fetches and extracts main content from web pages.

For Wikipedia URLs, uses the Wikipedia REST API to get clean, structured content.
For other pages, uses httpx + trafilatura with readability-lxml fallback.
"""

import json
import re
from typing import Any

import httpx
import trafilatura

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("content_extractor")

# Wikipedia API endpoint pattern
_WIKI_VI_PATTERN = re.compile(
    r"https?://vi\.wikipedia\.org/wiki/([^#?]+)", re.IGNORECASE
)


def _extract_wikipedia_title_from_url(url: str) -> str | None:
    """Return the article title (URL-decoded) from a vi.wikipedia.org URL."""
    m = _WIKI_VI_PATTERN.match(url)
    if m:
        from urllib.parse import unquote
        return unquote(m.group(1).replace("_", " "))
    return None


class ContentExtractor:
    """
    Extract main content from web pages.

    Wikipedia pages are fetched via the REST API for clean content.
    Other pages use trafilatura with readability-lxml fallback.
    """

    def __init__(
        self,
        timeout: int | None = None,
        max_retries: int | None = None,
    ):
        self.timeout = timeout or settings.FETCH_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.FETCH_MAX_RETRIES

    async def fetch(self, url: str) -> dict[str, Any]:
        """
        Fetch and extract content from URL.

        Returns:
            Dict with 'html', 'text', 'title', 'author', 'date', 'url', 'source'
        """
        # Route Wikipedia URLs through the REST API for clean, fast extraction
        wiki_title = _extract_wikipedia_title_from_url(url)
        if wiki_title:
            return await self._fetch_wikipedia(wiki_title, url)

        return await self._fetch_generic(url)

    # ------------------------------------------------------------------
    # Wikipedia REST API path
    # ------------------------------------------------------------------

    async def _fetch_wikipedia(self, title: str, original_url: str) -> dict[str, Any]:
        """Use Wikipedia REST API to get clean article HTML.

        Returns full article HTML without navigation boilerplate.
        Falls back to generic fetcher if the API call fails.
        """
        from urllib.parse import quote

        encoded = quote(title, safe="")
        api_url = f"https://vi.wikipedia.org/api/rest_v1/page/html/{encoded}"

        logger.info("wikipedia_api_fetch", title=title[:80])
        try:
            timeout = httpx.Timeout(connect=10.0, read=30.0, write=10.0, pool=5.0)
            async with httpx.AsyncClient(
                timeout=timeout,
                follow_redirects=True,
                headers={"User-Agent": "HistoriAI/1.0 (contact@historiai.com)"},
            ) as client:
                resp = await client.get(api_url)
                resp.raise_for_status()
                # Limit to 5MB to avoid blocking on huge articles
                content = await resp.aread()
                if len(content) > 5 * 1024 * 1024:
                    content = content[:5 * 1024 * 1024]
                raw_html = content.decode("utf-8", errors="replace")

            return {
                "html": raw_html,
                "text": "",
                "title": title,
                "author": "Wikipedia",
                "date": None,
                "url": original_url,
                "source": "wikipedia_api",
            }

        except Exception as exc:
            logger.warning(
                "wikipedia_api_failed", title=title[:60], error=str(exc)
            )
            # Fall back to generic fetcher
            return await self._fetch_generic(original_url)

    # ------------------------------------------------------------------
    # Generic web page path
    # ------------------------------------------------------------------

    async def _fetch_generic(self, url: str) -> dict[str, Any]:
        """Fetch a generic web page using httpx + trafilatura."""
        logger.info("fetching_url", url=url[:100])

        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "User-Agent": "HistoriAI/1.0 (contact@historiai.com)",
                },
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                html = response.text

            # Extract using trafilatura in thread pool to avoid blocking event loop
            import asyncio
            loop = asyncio.get_running_loop()
            extracted = await loop.run_in_executor(
                None,
                lambda: trafilatura.extract(
                    html,
                    include_comments=False,
                    include_tables=True,
                    include_images=False,
                    output_format="json",
                )
            )

            if extracted:
                data = json.loads(extracted)
                return {
                    "html": html,
                    "text": data.get("text", ""),
                    "title": data.get("title", ""),
                    "author": data.get("author"),
                    "date": data.get("date"),
                    "url": url,
                    "source": "trafilatura",
                }

            # Fallback to readability
            return await self._extract_readability(html, url)

        except httpx.TimeoutException:
            logger.error("fetch_timeout", url=url)
            raise ValueError(f"Timeout fetching URL: {url}")
        except httpx.HTTPStatusError as e:
            logger.error("fetch_http_error", url=url, status=e.response.status_code)
            raise ValueError(f"HTTP error {e.response.status_code} for URL: {url}")
        except Exception as e:
            logger.error("fetch_error", url=url, error=str(e))
            raise ValueError(f"Error fetching URL: {str(e)}")

    async def _extract_readability(self, html: str, url: str) -> dict[str, Any]:
        """Fallback extraction using readability."""
        try:
            from readability import Document
            doc = Document(html)
            return {
                "html": html,
                "text": doc.summary(),
                "title": doc.title(),
                "author": None,
                "date": None,
                "url": url,
                "source": "readability",
            }
        except Exception as e:
            logger.error("readability_error", error=str(e))
            return {
                "html": html,
                "text": "",
                "title": "",
                "author": None,
                "date": None,
                "url": url,
                "source": "none",
            }

    def detect_source_type(self, url: str, html: str | None = None) -> str:
        """
        Detect the type of content source.

        Returns:
            'wikipedia', 'article', 'pdf', 'doc', 'unknown'
        """
        url_lower = url.lower()

        if "wikipedia.org" in url_lower or "wikisource.org" in url_lower:
            return "wikipedia"
        if url_lower.endswith((".pdf", "?format=pdf")):
            return "pdf"
        if url_lower.endswith((".doc", ".docx")):
            return "doc"
        if "article" in url_lower or "news" in url_lower or "blog" in url_lower:
            return "article"

        return "unknown"
