"""Security headers and CSP configuration."""

from __future__ import annotations

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings


# ─── CSP & Security Headers ──────────────────────────────────────────────────────


CSP_POLICY = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline'; "  # Vite HMR in dev
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https:; "
    "font-src 'self' data:; "
    "connect-src 'self' https://api.openai.com https://api.anthropic.com https://*.langfuse.cloud; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self';"
)

SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": (
        "geolocation=(), camera=(), microphone=(), payment=(), usb=()"
    ),
    "Content-Security-Policy": CSP_POLICY,
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all HTTP responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if hasattr(response, "headers"):
            for header, value in SECURITY_HEADERS.items():
                response.headers[header] = value

            # Cache control: no-store for API responses, short max-age for static
            path = request.url.path
            if path.startswith("/api/") or path.startswith("/mcp"):
                response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
                response.headers["Pragma"] = "no-cache"

        return response
