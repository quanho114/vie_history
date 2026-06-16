"""Security utilities: JWT, password hashing, RBAC."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.user import User, get_bypass_user



# === PASSWORD HASHING ===
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """Hash password."""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")


# === JWT ===
security = HTTPBearer()


class TokenData(BaseModel):
    """Token payload data."""

    sub: str
    exp: datetime
    type: str = "access"


class TokenPayload(BaseModel):
    """Full token payload."""

    user_id: str
    email: str
    role: str
    exp: datetime
    type: str


def create_access_token(
    user_id: str,
    email: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": expire,
        "type": "access",
        "iat": datetime.now(timezone.utc),
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> TokenPayload:
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        return TokenPayload(
            user_id=payload["sub"],
            email=payload["email"],
            role=payload["role"],
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
            type=payload["type"],
        )
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


# === AUTH DEPENDENCIES ===
async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get current authenticated user."""
    token = credentials.credentials
    token_data = decode_token(token)

    if token_data.type != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
        )

    # Check expiration
    if datetime.now(timezone.utc) > token_data.exp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )

    if settings.APP_ENV == "testing":
        user = User(
            id=token_data.user_id,
            email=token_data.email,
            username=token_data.email.split("@")[0],
            hashed_password="",
            role=token_data.role,
        )
        return user

    try:
        result = await db.execute(select(User).where(User.id == token_data.user_id))
        user = result.scalar_one_or_none()
    except Exception:
        # No database available — fall back to bypass user
        user = None

    if user is None:
        # Check if this is a bypass token (dev mode)
        # Only allow bypass in testing environment with explicit flag
        if settings.APP_ENV == "testing" and token_data.user_id == "bypass-user-id":
            bypass_user = get_bypass_user()
            try:
                await db.merge(bypass_user)
                await db.commit()
            except Exception:
                await db.rollback()
            return bypass_user
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User | None:
    """Get current user if authenticated, otherwise None."""
    if credentials is None:
        return None

    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def require_admin(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    """Require admin role."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# === TYPE ALIASES ===
CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_current_user_optional)]
AdminUser = Annotated[User, Depends(require_admin)]


# === REFRESH TOKEN FUNCTIONS ===

def create_refresh_token(
    user_id: str,
    email: str,
    role: str,
    expires_days: int | None = None,
) -> str:
    """Create a refresh token with configurable expiry (default 30 days)."""
    expiry_days = expires_days or settings.REFRESH_TOKEN_EXPIRE_DAYS
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=expiry_days),
        "iat": datetime.now(timezone.utc),
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_refresh_token(token: str) -> dict | None:
    """Verify refresh token and return payload. Returns None if invalid or expired."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
        if payload.get("type") != "refresh":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except JWTError:
        return None


def rotate_refresh_token(token: str) -> tuple[str, str] | None:
    """Rotate refresh token: verify old one, issue new access + refresh token pair.

    Returns (new_access_token, new_refresh_token) on success.
    Returns None if the refresh token is invalid or expired.
    """
    payload = verify_refresh_token(token)
    if not payload:
        return None

    new_access = create_access_token(
        user_id=payload["sub"],
        email=payload["email"],
        role=payload["role"],
    )
    new_refresh = create_refresh_token(
        user_id=payload["sub"],
        email=payload["email"],
        role=payload["role"],
    )
    return new_access, new_refresh


# === SENSITIVE DATA MASKING ===

def mask_sensitive_keys(
    data: dict,
    patterns: list[str] | None = None,
) -> dict:
    """Mask API keys, tokens, and secrets in a dict."""
    if not data:
        return {}
    _patterns = patterns or ["key", "token", "secret", "password"]
    result = {}
    for k, v in data.items():
        if any(p in k.lower() for p in _patterns):
            if v and isinstance(v, str):
                result[k] = v[:4] + "****" if len(v) > 4 else "****"
            else:
                result[k] = None
        else:
            result[k] = v
    return result
