"""Authentication routes."""

import os
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import get_logger
from app.core.security import (
    get_current_user,
    get_password_hash,
    verify_password,
    create_access_token,
    rotate_refresh_token,
)
from app.models.user import User, get_bypass_user
from app.schemas.auth import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    TokenRefresh,
    TokenWithRefreshResponse,
    UserProfileUpdate,
)
from app.core.audit import get_audit_logger, AuditAction, AuditLevel

logger = get_logger("auth")


def mask_settings_keys(settings_dict: dict | None) -> dict:
    """Mask sensitive API keys in settings before returning to client."""
    if not settings_dict:
        return {}
    masked = dict(settings_dict)
    for key in ["gemini_key", "groq_key", "openai_key"]:
        if key in masked and masked[key]:
            masked[key] = "••••••••"
    return masked


def merge_settings(old_settings: dict | None, new_settings: dict | None) -> dict:
    """Merge new settings into old settings, preserving masked keys if unchanged."""
    old = dict(old_settings or {})
    new = dict(new_settings or {})
    for k, v in new.items():
        if k in ["gemini_key", "groq_key", "openai_key"] and v in ("••••••••", "********"):
            continue
        old[k] = v
    return old


DEV_BYPASS = (
    os.environ.get("APP_ENV") == "development"
    and os.environ.get("DEV_AUTH_BYPASS_ENABLED", "false").lower() == "true"
)

if DEV_BYPASS:
    import warnings
    warnings.warn(
        "DEV_AUTH_BYPASS is active — authentication is disabled. "
        "Do not set DEV_AUTH_BYPASS_ENABLED=true in production.",
        RuntimeWarning,
    )


router = APIRouter()


def _is_db_available(db: AsyncSession) -> bool:
    try:
        return db.is_active
    except Exception:
        return False


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user."""
    # Dev bypass: only skip on DB connection errors, not on all DB errors.
    # Requires explicit flag to prevent accidental bypass in misconfigured staging.
    if DEV_BYPASS and os.environ.get("ALLOW_DB_BYPASS_ON_ERROR", "false").lower() == "true":
        try:
            await db.execute(select(User).where(User.email == data.email))
            await db.execute(select(User).where(User.username == data.username))
        except DBAPIError as db_err:
            # Only bypass for connection-related errors, not for schema violations etc.
            error_msg = str(db_err).lower()
            if "connection" in error_msg or "network" in error_msg or "timeout" in error_msg:
                logger.warning(f"DEV_BYPASS: DB unavailable ({db_err}), creating bypass user")
                bypass_user = get_bypass_user()
                bypass_user.email = data.email
                bypass_user.username = data.username
                access_token = create_access_token(
                    user_id=bypass_user.id,
                    email=bypass_user.email,
                    role=bypass_user.role,
                )
                return TokenResponse(
                    access_token=access_token,
                    user=UserResponse(
                        id=bypass_user.id,
                        email=bypass_user.email,
                        username=bypass_user.username,
                        role=bypass_user.role,
                        settings=mask_settings_keys(bypass_user.settings),
                    ),
                )
            raise  # re-raise non-connection DB errors

    # Check if email exists
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Check if username exists
    result = await db.execute(select(User).where(User.username == data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    # Create user
    user = User(
        email=data.email,
        username=data.username,
        hashed_password=get_password_hash(data.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate token
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            role=user.role,
            settings=mask_settings_keys(user.settings),
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    data: UserLogin,
    db: AsyncSession = Depends(get_db),
):
    """Login and get access token."""
    # Dev bypass: try DB first, fall back to bypass user if unavailable
    try:
        result = await db.execute(select(User).where(User.email == data.email))
        user = result.scalar_one_or_none()
        if user is None or not verify_password(data.password, user.hashed_password):
            get_audit_logger().log_auth_login(
                email=data.email, ip_address="", success=False,
                error="Invalid credentials",
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )
    except DBAPIError as exc:
        if DEV_BYPASS:
            # No database — use bypass user with any credentials
            bypass_user = get_bypass_user()
            bypass_user.email = data.email
            access_token = create_access_token(
                user_id=bypass_user.id,
                email=bypass_user.email,
                role=bypass_user.role,
            )
            return TokenResponse(
                access_token=access_token,
                user=UserResponse(
                    id=bypass_user.id,
                    email=bypass_user.email,
                    username=bypass_user.username,
                    role=bypass_user.role,
                    settings=mask_settings_keys(bypass_user.settings),
                ),
            )
        raise exc

    # Generate token
    access_token = create_access_token(
        user_id=user.id,
        email=user.email,
        role=user.role,
    )

    get_audit_logger().log_auth_login(
        email=data.email,
        ip_address="",  # populated by middleware
        success=True,
        user_id=user.id,
        role=user.role,
    )

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            role=user.role,
            settings=mask_settings_keys(user.settings),
        ),
    )


@router.post("/refresh", response_model=TokenWithRefreshResponse)
async def refresh_tokens(
    data: TokenRefresh,
    db: AsyncSession = Depends(get_db),
):
    """Rotate refresh token and issue new access + refresh token pair."""
    result = rotate_refresh_token(data.refresh_token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    new_access, new_refresh = result

    # Decode to get user info (we already validated it in rotate_refresh_token)
    from jose import jwt as jose_jwt
    from app.core.config import settings as app_settings
    payload = jose_jwt.decode(
        new_access,
        app_settings.SECRET_KEY,
        algorithms=[app_settings.ALGORITHM],
    )
    user_id = payload["sub"]

    # Look up user
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return TokenWithRefreshResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        user=UserResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            role=user.role,
            settings=mask_settings_keys(user.settings),
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    """Get current user profile."""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        role=current_user.role,
        settings=mask_settings_keys(current_user.settings),
    )


@router.put("/profile", response_model=UserResponse)
async def update_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user profile and settings."""
    if current_user.id == "bypass-user-id":
        # Dev bypass mode
        if data.username is not None:
            current_user.username = data.username
        if data.email is not None:
            current_user.email = data.email
        if data.settings is not None:
            current_user.settings = merge_settings(current_user.settings, data.settings)
        return UserResponse(
            id=current_user.id,
            email=current_user.email,
            username=current_user.username,
            role=current_user.role,
            settings=mask_settings_keys(current_user.settings),
        )

    # Check email uniqueness if email is changed
    if data.email is not None and data.email != current_user.email:
        email_result = await db.execute(select(User).where(User.email == data.email))
        if email_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        current_user.email = data.email

    # Check username uniqueness if username is changed
    if data.username is not None and data.username != current_user.username:
        username_result = await db.execute(select(User).where(User.username == data.username))
        if username_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )
        current_user.username = data.username

    # Update password if requested
    if data.password is not None:
        current_user.hashed_password = get_password_hash(data.password)

    # Update settings if requested
    if data.settings is not None:
        from sqlalchemy.orm.attributes import flag_modified
        current_user.settings = merge_settings(current_user.settings, data.settings)
        flag_modified(current_user, "settings")

    db.add(current_user)
    await db.commit()
    await db.refresh(current_user)

    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        username=current_user.username,
        role=current_user.role,
        settings=mask_settings_keys(current_user.settings),
    )


from app.models.reset_request import ResetRequest
from app.schemas.auth import ResetRequestCreate

@router.post("/reset-request", status_code=status.HTTP_201_CREATED)
async def create_reset_request(
    data: ResetRequestCreate,
    db: AsyncSession = Depends(get_db),
):
    """Submit a new password reset request."""
    # Check if the user exists
    user_result = await db.execute(select(User).where(User.email == data.email))
    user = user_result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tài khoản email này chưa được đăng ký trong hệ thống",
        )
    
    # Check if there is already a pending request for this email
    existing_result = await db.execute(
        select(ResetRequest)
        .where(ResetRequest.email == data.email)
        .where(ResetRequest.status == "pending")
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Yêu cầu khôi phục mật khẩu trước đó của bạn đang chờ xử lý",
        )
        
    reset_req = ResetRequest(
        email=data.email,
        username=data.username or user.username,
        reason=data.reason,
        status="pending",
    )
    db.add(reset_req)
    await db.commit()
    return {"status": "success", "message": "Yêu cầu khôi phục mật khẩu đã được gửi đến Ban Quản trị"}

