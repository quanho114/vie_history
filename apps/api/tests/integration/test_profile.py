"""Integration tests for user profile and settings update route.

Tests cover:
- Basic profile updates (username, email)
- Password update and hash verification
- Syncing and merging settings (JSONB)
- Sensitive API keys masking with ••••••••
- Retaining existing API keys when client sends •••••••• placeholder
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.user import User
from app.core.security import get_password_hash, verify_password

# --- Helper classes ---

class MockDBResult:
    def __init__(self, value: Any = None):
        self.value = value

    def scalar_one_or_none(self) -> Any:
        return self.value

    def scalar_one(self) -> Any:
        return self.value

    def scalar(self) -> Any:
        return self.value


def auth_headers(user_id: str = "user-001") -> dict[str, str]:
    """Return mock auth headers for a test user."""
    from datetime import datetime, timedelta, timezone
    from jose import jwt
    from app.core.config import settings

    payload = {
        "sub": user_id,
        "email": "test@example.com",
        "role": "user",
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        "type": "access",
    }
    token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
class TestUserProfileUpdate:
    """Integration tests for PUT /api/v1/auth/profile using AsyncClient to preserve overrides."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self) -> None:
        # Resolve dependencies dynamically to ensure perfect match
        from app.core.security import get_current_user
        from app.core.database import get_db

        # Create a fresh, realistic User model instance
        self.test_user = User(
            id="user-001",
            email="test@example.com",
            username="testuser",
            hashed_password=get_password_hash("OldSecurePass123!"),
            role="user",
            settings={
                "theme": "light",
                "language": "vi",
                "gemini_key": "super-secret-gemini-key",
                "openai_key": "super-secret-openai-key"
            }
        )
        
        # Setup mock db session
        self.mock_db = AsyncMock(spec=AsyncSession)
        self.mock_db.execute = AsyncMock(return_value=MockDBResult(None))
        self.mock_db.commit = AsyncMock()
        self.mock_db.refresh = AsyncMock()
        self.mock_db.add = MagicMock()

        # Apply overrides
        app.dependency_overrides[get_current_user] = lambda: self.test_user
        app.dependency_overrides[get_db] = lambda: self.mock_db

        yield

        # Clean overrides
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_db, None)

    async def test_update_profile_basic_success(self) -> None:
        """Cập nhật thông tin cơ bản (username, email) thành công."""
        payload = {
            "username": "newusername",
            "email": "newemail@example.com"
        }
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/auth/profile",
                json=payload,
                headers=auth_headers(),
            )
            
            assert resp.status_code == 200
            data = resp.json()
            
            # Verify response schema and contents
            assert data["username"] == "newusername"
            assert data["email"] == "newemail@example.com"
            assert data["id"] == "user-001"
            
            # Verify database actions
            assert self.test_user.username == "newusername"
            assert self.test_user.email == "newemail@example.com"
            self.mock_db.commit.assert_called_once()
            self.mock_db.refresh.assert_called_once()

    async def test_update_profile_duplicate_email(self) -> None:
        """Cập nhật email trùng sẽ báo lỗi 400 Bad Request."""
        payload = {
            "email": "duplicate@example.com"
        }
        
        # Mock database to find an existing user with this email
        existing_user = User(id="user-002", email="duplicate@example.com", username="other")
        self.mock_db.execute.return_value = MockDBResult(existing_user)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/auth/profile",
                json=payload,
                headers=auth_headers(),
            )
            assert resp.status_code == 400
            assert "Email already registered" in resp.json()["detail"]

    async def test_update_profile_duplicate_username(self) -> None:
        """Cập nhật username trùng sẽ báo lỗi 400 Bad Request."""
        payload = {
            "username": "takenusername"
        }
        
        # Mock database to find an existing user with this username
        existing_user = User(id="user-002", email="other@example.com", username="takenusername")
        self.mock_db.execute.return_value = MockDBResult(existing_user)
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/auth/profile",
                json=payload,
                headers=auth_headers(),
            )
            assert resp.status_code == 400
            assert "Username already taken" in resp.json()["detail"]

    async def test_update_profile_password_success(self) -> None:
        """Cập nhật mật khẩu mã hóa mới chính xác."""
        payload = {
            "password": "NewSecurePass987!"
        }
        
        # Verify old password works first
        assert verify_password("OldSecurePass123!", self.test_user.hashed_password) is True
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/auth/profile",
                json=payload,
                headers=auth_headers(),
            )
            
            assert resp.status_code == 200
            
            # Verify password was updated and hashed correctly
            assert verify_password("NewSecurePass987!", self.test_user.hashed_password) is True
            assert verify_password("OldSecurePass123!", self.test_user.hashed_password) is False
            
            self.mock_db.commit.assert_called_once()

    async def test_update_profile_merge_settings(self) -> None:
        """Đồng bộ và ghép cài đặt (merge_settings) thành công."""
        payload = {
            "settings": {
                "theme": "dark",
                "rag_mode": "hybrid",
                "chunk_limit": 12
            }
        }
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/auth/profile",
                json=payload,
                headers=auth_headers(),
            )
            
            assert resp.status_code == 200
            data = resp.json()
            
            # Check merged settings in response
            assert data["settings"]["theme"] == "dark"
            assert data["settings"]["language"] == "vi"  # preserved from old settings
            assert data["settings"]["rag_mode"] == "hybrid"
            assert data["settings"]["chunk_limit"] == 12
            
            # Check updated database state
            assert self.test_user.settings["theme"] == "dark"
            assert self.test_user.settings["language"] == "vi"
            assert self.test_user.settings["rag_mode"] == "hybrid"
            assert self.test_user.settings["chunk_limit"] == 12

    async def test_update_profile_masks_sensitive_api_keys(self) -> None:
        """Che dấu API keys nhạy cảm trong response payload dưới dạng ••••••••."""
        payload = {
            "settings": {
                "gemini_key": "new-gemini-secret-key",
                "groq_key": "new-groq-secret-key"
            }
        }
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/auth/profile",
                json=payload,
                headers=auth_headers(),
            )
            
            assert resp.status_code == 200
            data = resp.json()
            
            # Verify masked keys in the response body
            assert data["settings"]["gemini_key"] == "••••••••"
            assert data["settings"]["groq_key"] == "••••••••"
            assert data["settings"]["openai_key"] == "••••••••"  # also masked even though not modified
            
            # Verify actual plain keys are stored in the database object
            assert self.test_user.settings["gemini_key"] == "new-gemini-secret-key"
            assert self.test_user.settings["groq_key"] == "new-groq-secret-key"
            assert self.test_user.settings["openai_key"] == "super-secret-openai-key"

    async def test_update_profile_retains_placeholder_keys(self) -> None:
        """Giữ nguyên API keys cũ khi client gửi chuỗi placeholder ••••••••."""
        payload = {
            "settings": {
                "theme": "dark",
                "gemini_key": "••••••••",
                "openai_key": "••••••••",
                "groq_key": "brand-new-groq-key"
            }
        }
        
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                "/api/v1/auth/profile",
                json=payload,
                headers=auth_headers(),
            )
            
            assert resp.status_code == 200
            data = resp.json()
            
            # Verify response is masked
            assert data["settings"]["gemini_key"] == "••••••••"
            assert data["settings"]["openai_key"] == "••••••••"
            assert data["settings"]["groq_key"] == "••••••••"
            
            # Verify actual database values:
            # gemini_key & openai_key should retain old values, groq_key should take new value
            assert self.test_user.settings["gemini_key"] == "super-secret-gemini-key"
            assert self.test_user.settings["openai_key"] == "super-secret-openai-key"
            assert self.test_user.settings["groq_key"] == "brand-new-groq-key"
