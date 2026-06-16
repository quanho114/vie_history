# apps/api/tests/unit/test_repositories.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.repositories.session import SessionRepository, MessageRepository


class TestSessionRepository:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        db.get = AsyncMock(return_value=None)
        result = MagicMock()
        result.scalar_one_or_none = MagicMock(return_value=None)
        db.execute = AsyncMock(return_value=result)
        return db

    @pytest.mark.asyncio
    async def test_get_by_id_returns_none_when_not_found(self, mock_db):
        repo = SessionRepository(mock_db)
        result = await repo.get_by_id("nonexistent-id")
        assert result is None


class TestMessageRepository:
    @pytest.fixture
    def mock_db(self):
        db = AsyncMock()
        result = MagicMock()
        result.scalars = MagicMock()
        result.scalars().all = MagicMock(return_value=[])
        db.execute = AsyncMock(return_value=result)
        return db

    @pytest.mark.asyncio
    async def test_get_conversation_context_empty(self, mock_db):
        repo = MessageRepository(mock_db)
        context = await repo.get_conversation_context("session-123", "current query")
        assert context == ""
