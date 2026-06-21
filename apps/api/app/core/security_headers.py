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


class SecurityHeadersMiddleware:
    """Pure ASGI Middleware to add security headers to all HTTP responses."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                
                # Filter out any duplicate security headers
                security_header_names = {h.lower() for h in SECURITY_HEADERS.keys()}
                headers = [
                    (name, val) for name, val in headers 
                    if name.decode("latin-1").lower() not in security_header_names
                ]
                
                # Append the security headers
                for header, value in SECURITY_HEADERS.items():
                    headers.append((header.encode("latin-1"), value.encode("latin-1")))

                # Cache control: no-store for API responses, short max-age for static
                path = scope.get("path", "")
                if path.startswith("/api/") or path.startswith("/mcp"):
                    # Remove existing Cache-Control or Pragma
                    headers = [
                        (name, val) for name, val in headers
                        if name.lower() not in (b"cache-control", b"pragma")
                    ]
                    headers.append((b"cache-control", b"no-store, no-cache, must-revalidate, private"))
                    headers.append((b"pragma", b"no-cache"))

                message["headers"] = headers

            await send(message)

        await self.app(scope, receive, send_wrapper)

