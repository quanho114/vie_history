"""GZip response compression middleware."""
from __future__ import annotations

from gzip import GzipFile
from io import BytesIO
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

MIN_SIZE = 500  # Don't compress responses smaller than 500 bytes


class GZipCompressionMiddleware(BaseHTTPMiddleware):
    """Compress responses with GZip for text-based content types.

    Only compresses responses when:
    - Client sends Accept-Encoding containing "gzip"
    - Response status is 200
    - Content-Type is text-based or application/json/xml
    - Response body is at least minimum_size bytes

    Features:
    - Configurable compression level (1-9, default 6)
    - Configurable minimum size threshold
    - Preserves all original headers
    - Adds Content-Encoding: gzip and Vary: Accept-Encoding
    """

    def __init__(
        self,
        app,
        minimum_size: int = MIN_SIZE,
        compress_level: int = 6,
    ):
        super().__init__(app)
        self.minimum_size = minimum_size
        self.compress_level = max(1, min(9, compress_level))  # Clamp to 1-9

    def _should_compress(self, request: Request, response: Response) -> bool:
        """Determine if the response should be compressed."""
        # Only compress successful responses
        if response.status_code != 200:
            return False

        # Check Accept-Encoding header
        accept_encoding = request.headers.get("Accept-Encoding", "")
        if "gzip" not in accept_encoding.lower():
            return False

        # Check Content-Type
        content_type = response.headers.get("Content-Type", "")
        compressible_types = [
            "text/",
            "application/json",
            "application/xml",
            "application/vnd.api+json",
        ]
        if not any(ct in content_type for ct in compressible_types):
            return False

        return True

    def _compress(self, body: bytes) -> bytes:
        """Compress body using GZip."""
        gzip_buffer = BytesIO()
        with GzipFile(
            fileobj=gzip_buffer,
            mode="wb",
            compresslevel=self.compress_level,
        ) as f:
            f.write(body)
        return gzip_buffer.getvalue()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip if client doesn't accept gzip
        accept_encoding = request.headers.get("Accept-Encoding", "")
        if "gzip" not in accept_encoding.lower():
            return await call_next(request)

        response = await call_next(request)

        # Skip non-200 responses
        if response.status_code != 200:
            return response

        # Skip already compressed responses
        content_encoding = response.headers.get("Content-Encoding", "")
        if content_encoding:
            return response

        # Check content type
        content_type = response.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            return response

        compressible = any(
            ct in content_type
            for ct in ("text/", "application/json", "application/xml")
        )
        if not compressible:
            return response

        # Read and compress body
        body = b""
        async for chunk in response.body_iterator:
            body += chunk if isinstance(chunk, bytes) else chunk.encode()

        if len(body) < self.minimum_size:
            return Response(
                content=body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        compressed = self._compress(body)

        # Build new headers, removing Content-Length (no longer valid)
        headers = {k: v for k, v in response.headers.items() if k.lower() != "content-length"}
        headers["Content-Encoding"] = "gzip"
        headers["Vary"] = "Accept-Encoding"

        return Response(
            content=compressed,
            status_code=response.status_code,
            headers=headers,
            media_type=response.media_type,
        )
