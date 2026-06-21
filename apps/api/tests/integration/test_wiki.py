"""Integration tests for Wiki context endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.wiki import WikiPage
from tests.integration.test_api import auth_headers, make_test_user


@pytest.mark.asyncio
class TestWikiContextEndpoints:
    """Tests for Wiki Context RAG integration endpoints."""

    async def test_get_context_requires_auth(self) -> None:
        """Without authentication, wiki context endpoint must return 401/403."""
        # Ensure overrides are clean
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/wiki/pages/some-slug/context")
            assert resp.status_code in (401, 403)

    async def test_get_context_not_found(self) -> None:
        """If wiki page does not exist, return 404."""
        async_session = AsyncMock()
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = None
        async_session.execute.return_value = mock_execute_result

        app.dependency_overrides[get_current_user] = make_test_user
        app.dependency_overrides[get_db] = lambda: async_session

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                resp = await client.get("/api/v1/wiki/pages/nonexistent-slug/context", headers=auth_headers())
                assert resp.status_code == 404
        finally:
            app.dependency_overrides[get_current_user] = make_test_user
            app.dependency_overrides.pop(get_db, None)

    async def test_get_context_success(self) -> None:
        """Successfully retrieve context and parsed sources for a wiki page."""
        mock_page = MagicMock(spec=WikiPage)
        mock_page.title = "Trận Điện Biên Phủ"
        mock_page.summary = "Trận đánh quyết định năm 1954"
        mock_page.period = "1945-1954"
        mock_page.event_type = "military"
        mock_page.content = {
            "references": "Tài liệu lịch sử A\nTài liệu lịch sử B"
        }

        async_session = AsyncMock()
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = mock_page
        async_session.execute.return_value = mock_execute_result

        app.dependency_overrides[get_current_user] = make_test_user
        app.dependency_overrides[get_db] = lambda: async_session

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                resp = await client.get("/api/v1/wiki/pages/dien-bien-phu/context", headers=auth_headers())
                assert resp.status_code == 200
                data = resp.json()
                
                assert data["context"]["title"] == "Trận Điện Biên Phủ"
                assert data["context"]["summary"] == "Trận đánh quyết định năm 1954"
                assert "1945-1954" in data["context"]["entities"]
                assert "military" in data["context"]["entities"]
                
                assert len(data["sources"]) == 2
                assert data["sources"][0]["title"] == "Tài liệu lịch sử A"
                assert data["sources"][1]["title"] == "Tài liệu lịch sử B"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
