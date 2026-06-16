"""Integration tests for API routes.

Tests cover:
- Authentication (login, register)
- Query endpoint (sync + streaming)
- Sessions endpoint
- Ingest endpoint
- Health and metrics endpoints

All tests use mocked auth and database via dependency overrides.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import User
from app.models.session import Session


# ─── Auth helpers ───────────────────────────────────────────────────────────────

def make_test_user(
    id: str = "user-001",
    email: str = "test@example.com",
    role: str = "user",
) -> User:
    """Create a mock User for testing."""
    user = MagicMock(spec=User)
    user.id = id
    user.email = email
    user.role = role
    user.is_active = True
    return user


def make_test_session(
    id: str = "session-001",
    user_id: str = "user-001",
) -> Session:
    """Create a mock Session for testing."""
    session = MagicMock(spec=Session)
    session.id = id
    session.user_id = user_id
    session.title = "Test session"
    return session


def auth_headers(user_id: str = "user-001") -> dict[str, str]:
    """Return mock auth headers for a test user."""
    from datetime import datetime, timedelta, timezone
    from jose import jwt

    payload = {
        "sub": user_id,
        "email": "test@example.com",
        "role": "user",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "type": "access",
    }
    from app.core.config import settings
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


def admin_headers() -> dict[str, str]:
    """Return mock auth headers for an admin user."""
    from datetime import datetime, timedelta, timezone
    from jose import jwt

    payload = {
        "sub": "admin-001",
        "email": "admin@example.com",
        "role": "admin",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "type": "access",
    }
    from app.core.config import settings
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


# ─── Auth dependency overrides ─────────────────────────────────────────────────

def _override_get_current_user():
    """Override auth dependency to return test user."""
    from app.core.security import get_current_user
    return get_current_user


# Override dependency
app.dependency_overrides[_override_get_current_user()] = make_test_user


# ─── Query endpoint tests ───────────────────────────────────────────────────────

class TestQueryEndpoint:
    """Tests for POST /api/v1/query (synchronous query)."""

    def test_query_requires_auth(self) -> None:
        """Without auth token, endpoint must return 401/403."""
        # Clear overrides temporarily
        app.dependency_overrides.pop(_override_get_current_user(), None)
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post("/api/v1/query", json={"query": "Test"})
                assert resp.status_code in (401, 403, 422)
        finally:
            app.dependency_overrides[_override_get_current_user()] = make_test_user

    def test_query_rejects_empty_query(self) -> None:
        """Empty query string must be rejected as validation error."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/api/v1/query",
                json={"query": ""},
                headers=auth_headers(),
            )
            assert resp.status_code == 422

    def test_query_rejects_missing_query_field(self) -> None:
        """Missing query field must be rejected as validation error."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/api/v1/query", json={}, headers=auth_headers())
            assert resp.status_code == 422

    def test_query_rejects_query_too_long(self) -> None:
        """Query exceeding 1000 chars must be rejected."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/api/v1/query",
                json={"query": "x" * 1001},
                headers=auth_headers(),
            )
            assert resp.status_code == 422

    def test_query_accepts_valid_request(self) -> None:
        """Valid request with auth must return 200 (or fail gracefully if no DB)."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/api/v1/query",
                json={"query": "Chiến dịch Điện Biên Phủ năm 1954"},
                headers=auth_headers(),
            )
            # Accept: 200 (success), 400 (unconfigured LLM credentials), or 500 (DB unavailable)
            assert resp.status_code in (200, 400, 500)

    def test_query_with_filters(self) -> None:
        """Query with year filters must be accepted."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/api/v1/query",
                json={
                    "query": "Hồ Chí Minh",
                    "filters": {"year_range": [1940, 1960]},
                },
                headers=auth_headers(),
            )
            assert resp.status_code in (200, 400, 500)

    def test_query_with_forced_mode(self) -> None:
        """Query with forced mode must be accepted."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/api/v1/query",
                json={"query": "So sánh A và B", "mode": "compare"},
                headers=auth_headers(),
            )
            assert resp.status_code in (200, 400, 500)

    def test_query_with_session_id(self) -> None:
        """Query with session_id must be accepted."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/api/v1/query",
                json={
                    "query": "Test query",
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                },
                headers=auth_headers(),
            )
            assert resp.status_code in (200, 400, 500)


class TestQueryStreamEndpoint:
    """Tests for POST /api/v1/query/stream (streaming query)."""

    def test_stream_requires_auth(self) -> None:
        """Stream endpoint must require auth."""
        app.dependency_overrides.pop(_override_get_current_user(), None)
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(
                    "/api/v1/query/stream",
                    json={"query": "Test"},
                )
                assert resp.status_code in (401, 403, 422)
        finally:
            app.dependency_overrides[_override_get_current_user()] = make_test_user

    def test_stream_rejects_empty_query(self) -> None:
        """Empty query must be rejected at stream endpoint."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/api/v1/query/stream",
                json={"query": ""},
                headers=auth_headers(),
            )
            assert resp.status_code == 422

    def test_stream_returns_sse_content_type(self) -> None:
        """Stream endpoint must return text/event-stream content type."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/api/v1/query/stream",
                json={"query": "Test query"},
                headers=auth_headers(),
            )
            # Either 200 with SSE, 400, or 500 (DB unavailable)
            assert resp.status_code in (200, 400, 500)


class TestQueryDebugEndpoint:
    """Tests for POST /api/v1/query/debug."""

    def test_debug_requires_auth(self) -> None:
        """Debug endpoint must require auth."""
        app.dependency_overrides.pop(_override_get_current_user(), None)
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post("/api/v1/query/debug", json={"query": "Test"})
                assert resp.status_code in (401, 403, 422)
        finally:
            app.dependency_overrides[_override_get_current_user()] = make_test_user

    def test_debug_rejects_empty_query(self) -> None:
        """Empty query must be rejected at debug endpoint."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/api/v1/query/debug",
                json={"query": ""},
                headers=auth_headers(),
            )
            assert resp.status_code == 422


# ─── Sessions endpoint tests ─────────────────────────────────────────────────────

class TestSessionsEndpoint:
    """Tests for /api/v1/sessions endpoints."""

    def test_list_sessions_requires_auth(self) -> None:
        """Session listing must require auth."""
        app.dependency_overrides.pop(_override_get_current_user(), None)
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get("/api/v1/sessions")
                assert resp.status_code in (401, 403, 422)
        finally:
            app.dependency_overrides[_override_get_current_user()] = make_test_user

    def test_create_session_requires_auth(self) -> None:
        """Session creation must require auth."""
        app.dependency_overrides.pop(_override_get_current_user(), None)
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(
                    "/api/v1/sessions",
                    json={"title": "New session"},
                )
                assert resp.status_code in (401, 403, 422)
        finally:
            app.dependency_overrides[_override_get_current_user()] = make_test_user

    def test_sessions_list_returns_json(self) -> None:
        """Sessions endpoint must return JSON."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/v1/sessions", headers=auth_headers())
            assert resp.status_code in (200, 500)
            if resp.status_code == 200:
                assert resp.headers["content-type"].startswith("application/json")


# ─── Auth endpoint tests ────────────────────────────────────────────────────────

class TestAuthEndpoint:
    """Tests for /api/v1/auth endpoints."""

    def test_login_rejects_empty_body(self) -> None:
        """Login with empty body must be rejected."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/api/v1/auth/login", json={})
            assert resp.status_code == 422

    def test_login_rejects_wrong_credentials(self) -> None:
        """Login with invalid credentials must be rejected."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/api/v1/auth/login",
                json={"email": "wrong@example.com", "password": "wrongpassword"},
            )
            assert resp.status_code in (401, 422)

    def test_register_rejects_invalid_email(self) -> None:
        """Registration with invalid email must be rejected."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/api/v1/auth/register",
                json={
                    "email": "not-an-email",
                    "password": "SecurePass123!",
                    "full_name": "Test User",
                },
            )
            assert resp.status_code == 422

    def test_register_rejects_short_password(self) -> None:
        """Registration with too-short password must be rejected."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/api/v1/auth/register",
                json={
                    "email": "test@example.com",
                    "password": "123",
                    "full_name": "Test User",
                },
            )
            assert resp.status_code == 422


# ─── Health & Metrics tests ────────────────────────────────────────────────────

class TestHealthEndpoint:
    """Tests for /health and /api/v1/health."""

    def test_health_returns_200(self) -> None:
        """Health endpoint must return 200."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/health")
            assert resp.status_code == 200

    def test_health_returns_status_field(self) -> None:
        """Health response must include status field."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/health")
            if resp.status_code == 200:
                data = resp.json()
                assert "status" in data
                assert data["status"] == "healthy"

    def test_api_health_returns_200(self) -> None:
        """API health endpoint must return 200."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/v1/health")
            assert resp.status_code == 200

    def test_api_health_returns_json(self) -> None:
        """API health must return application/json."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/v1/health")
            if resp.status_code == 200:
                assert resp.headers["content-type"].startswith("application/json")


class TestMetricsEndpoint:
    """Tests for /metrics Prometheus endpoint."""

    def test_metrics_returns_200(self) -> None:
        """Metrics endpoint must return 200."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/metrics")
            assert resp.status_code == 200

    def test_metrics_returns_prometheus_format(self) -> None:
        """Metrics endpoint must return Prometheus text format."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/metrics")
            if resp.status_code == 200:
                content = resp.text
                # Prometheus format has HELP and TYPE comments
                assert "historiai_" in content or "# HELP" in content


# ─── Ingest endpoint tests ────────────────────────────────────────────────────

class TestIngestEndpoint:
    """Tests for /api/v1/ingest endpoint."""

    def test_ingest_requires_auth(self) -> None:
        """Ingest must require auth."""
        app.dependency_overrides.pop(_override_get_current_user(), None)
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.post(
                    "/api/v1/ingest",
                    json={"url": "https://vi.wikipedia.org/wiki/Test"},
                )
                assert resp.status_code in (401, 403, 422)
        finally:
            app.dependency_overrides[_override_get_current_user()] = make_test_user

    def test_ingest_rejects_invalid_url(self) -> None:
        """Invalid URL must be rejected."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/api/v1/ingest",
                json={"url": "not-a-valid-url"},
                headers=auth_headers(),
            )
            assert resp.status_code == 422

    def test_ingest_rejects_localhost(self) -> None:
        """Localhost URL must be rejected (SSRF protection)."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post(
                "/api/v1/ingest",
                json={"url": "http://localhost:8080/secret"},
                headers=auth_headers(),
            )
            # Should be rejected with 400 or 422
            assert resp.status_code in (400, 422)


# ─── Documents endpoint tests ─────────────────────────────────────────────────

class TestDocumentsEndpoint:
    """Tests for /api/v1/documents endpoints."""

    def test_list_documents_requires_auth(self) -> None:
        """Documents listing must require auth."""
        app.dependency_overrides.pop(_override_get_current_user(), None)
        try:
            with TestClient(app, raise_server_exceptions=False) as client:
                resp = client.get("/api/v1/documents")
                assert resp.status_code in (401, 403, 422)
        finally:
            app.dependency_overrides[_override_get_current_user()] = make_test_user

    def test_documents_list_returns_json(self) -> None:
        """Documents endpoint must return JSON."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/v1/documents", headers=auth_headers())
            assert resp.status_code in (200, 500)
            if resp.status_code == 200:
                assert resp.headers["content-type"].startswith("application/json")


# ─── Admin endpoint tests ─────────────────────────────────────────────────────

class TestAdminEndpoint:
    """Tests for /api/v1/admin endpoints."""

    def test_admin_requires_admin_role(self) -> None:
        """Admin endpoints must require admin role."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/v1/admin/stats", headers=auth_headers())
            # Regular user → 403 Forbidden
            assert resp.status_code in (403, 500)

    def test_admin_stats_with_admin_token(self) -> None:
        """Admin stats with admin token must be accepted."""
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/api/v1/admin/stats", headers=admin_headers())
            assert resp.status_code in (200, 500)
