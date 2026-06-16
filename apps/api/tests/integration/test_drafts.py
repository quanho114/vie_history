"""Integration tests for Knowledge Drafts (HITL) endpoints."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.evolution import KnowledgeDraft
from app.models.graph import KnowledgeNode, KnowledgeEdge
from tests.integration.test_api import auth_headers, make_test_user


@pytest.mark.asyncio
class TestDraftsEndpoints:
    """Tests for Knowledge Evolution HITL endpoints."""

    async def test_list_drafts_requires_auth(self) -> None:
        """Without auth, drafts list must return 401/403."""
        # Ensure overrides are clean
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
            resp = await client.get("/api/v1/graph/drafts")
            assert resp.status_code in (401, 403)

    async def test_list_drafts_success(self) -> None:
        """Admin/User can list drafts successfully."""
        now = datetime.now(timezone.utc)
        mock_draft1 = MagicMock(spec=KnowledgeDraft)
        mock_draft1.id = "draft-1"
        mock_draft1.change_type = "add_node"
        mock_draft1.status = "pending"
        mock_draft1.draft_data = {"name": "Genève"}
        mock_draft1.source_info = {}
        mock_draft1.created_at = now
        mock_draft1.updated_at = now

        async_session = AsyncMock()
        mock_execute_result = MagicMock()
        mock_execute_result.scalars.return_value.all.return_value = [mock_draft1]
        async_session.execute.return_value = mock_execute_result

        # Set overrides
        app.dependency_overrides[get_current_user] = make_test_user
        app.dependency_overrides[get_db] = lambda: async_session

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                resp = await client.get("/api/v1/graph/drafts", headers=auth_headers())
                assert resp.status_code == 200
                data = resp.json()
                assert len(data) == 1
                assert data[0]["id"] == "draft-1"
                assert data[0]["change_type"] == "add_node"
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)

    @patch("app.api.routes.graph.Neo4jService")
    async def test_review_draft_reject(self, mock_neo4j_class) -> None:
        """Rejecting a draft updates status to rejected and does not write to Neo4j."""
        now = datetime.now(timezone.utc)
        mock_draft = MagicMock(spec=KnowledgeDraft)
        mock_draft.id = "draft-1"
        mock_draft.change_type = "add_node"
        mock_draft.status = "pending"
        mock_draft.draft_data = {"name": "Genève"}
        mock_draft.source_info = {}
        mock_draft.created_at = now
        mock_draft.updated_at = now

        async_session = AsyncMock()
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = mock_draft
        async_session.execute.return_value = mock_execute_result

        # Set overrides
        app.dependency_overrides[get_current_user] = make_test_user
        app.dependency_overrides[get_db] = lambda: async_session

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                resp = await client.post(
                    "/api/v1/graph/drafts/draft-1/review",
                    json={"status": "rejected"},
                    headers=auth_headers(),
                )
                assert resp.status_code == 200
                assert mock_draft.status == "rejected"
                mock_neo4j_class.assert_not_called()
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)

    @patch("app.api.routes.graph.Neo4jService")
    @patch("app.api.routes.graph._svc")
    async def test_review_draft_approve_node(self, mock_graph_service, mock_neo4j_class) -> None:
        """Approving add_node draft upserts node in Postgres and Neo4j."""
        now = datetime.now(timezone.utc)
        mock_draft = MagicMock(spec=KnowledgeDraft)
        mock_draft.id = "draft-1"
        mock_draft.change_type = "add_node"
        mock_draft.status = "pending"
        mock_draft.draft_data = {"name": "Chiến dịch Điện Biên Phủ", "node_type": "Battle", "slug": "dien-bien-phu", "description": "1954"}
        mock_draft.source_info = {}
        mock_draft.created_at = now
        mock_draft.updated_at = now

        async_session = AsyncMock()
        mock_execute_result = MagicMock()
        mock_execute_result.scalar_one_or_none.return_value = mock_draft
        async_session.execute.return_value = mock_execute_result

        # Mock Neo4jService
        mock_neo4j_instance = MagicMock()
        mock_neo4j_instance.create_node = AsyncMock()
        mock_neo4j_class.return_value = mock_neo4j_instance

        # Mock GraphService
        mock_graph_service._upsert_node = AsyncMock()

        # Set overrides
        app.dependency_overrides[get_current_user] = make_test_user
        app.dependency_overrides[get_db] = lambda: async_session

        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
                resp = await client.post(
                    "/api/v1/graph/drafts/draft-1/review",
                    json={"status": "approved"},
                    headers=auth_headers(),
                )
                assert resp.status_code == 200
                assert mock_draft.status == "approved"
                
                # Verify PG call
                mock_graph_service._upsert_node.assert_called_once()
                # Verify Neo4j call
                mock_neo4j_instance.create_node.assert_called_once_with(
                    node_type="Battle",
                    name="Chiến dịch Điện Biên Phủ",
                    slug="dien-bien-phu",
                    description="1954",
                    metadata_json={"source": "hitl_evolution"}
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)
            app.dependency_overrides.pop(get_db, None)
