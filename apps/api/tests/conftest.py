# apps/api/tests/conftest.py
"""Pytest fixtures for HistoriAI tests."""
import os
os.environ["APP_ENV"] = "testing"

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db():
    """Mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.close = AsyncMock()
    return session


@pytest.fixture
def mock_cache():
    """Mock Redis cache."""
    cache = AsyncMock()
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    cache.exists = AsyncMock(return_value=False)
    return cache


@pytest.fixture
def mock_llm():
    """Mock LLM client."""
    llm = AsyncMock()
    llm.generate = AsyncMock(return_value="Đây là một câu trả lời mẫu về lịch sử Việt Nam.")
    return llm


@pytest.fixture
def mock_embedder():
    """Mock embedder."""
    embedder = MagicMock()
    embedder.embed = MagicMock(return_value=[[0.1] * 384])
    embedder.embed_async = AsyncMock(return_value=[[0.1] * 384])
    return embedder


@pytest.fixture
def sample_chunks():
    """Sample document chunks for testing."""
    return [
        {
            "chunk_id": "chunk_001",
            "document_id": "doc_001",
            "document_title": "Chiến dịch Điện Biên Phủ",
            "content": "Chiến dịch Điện Biên Phủ diễn ra từ tháng 3 đến tháng 5 năm 1954.",
            "score": 0.92,
            "vector_score": 0.85,
            "bm25_score": 0.78,
            "cross_encoder_score": 0.88,
            "rerank_score": 0.90,
        },
        {
            "chunk_id": "chunk_002",
            "document_id": "doc_001",
            "document_title": "Chiến dịch Điện Biên Phủ",
            "content": "Tướng Đờ Cát của Pháp chỉ huy quân đội viễn chinh.",
            "score": 0.87,
            "vector_score": 0.80,
            "bm25_score": 0.72,
            "cross_encoder_score": 0.82,
            "rerank_score": 0.85,
        },
    ]


@pytest.fixture
def sample_user():
    """Sample user for authentication tests."""
    from app.models.user import User
    return User(
        id="test-user-id",
        email="test@example.com",
        username="test_user",
        hashed_password="$2b$12$test_hash",
        role="user",
        settings={},
    )


@pytest.fixture
def sample_admin():
    """Sample admin user."""
    from app.models.user import User
    return User(
        id="test-admin-id",
        email="admin@example.com",
        username="admin_user",
        hashed_password="$2b$12$admin_hash",
        role="admin",
        settings={},
    )


@pytest.fixture
def client():
    """FastAPI TestClient fixture."""
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


@pytest.fixture
def auth_headers():
    """Mock auth headers for testing."""
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from app.core.config import settings

    payload = {
        "sub": "test-user-id",
        "email": "test@example.com",
        "role": "user",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "type": "access",
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"Authorization": f"Bearer {token}"}
