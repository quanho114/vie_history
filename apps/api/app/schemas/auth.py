"""Auth schemas."""

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""

    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)


class UserLogin(BaseModel):
    """Schema for user login."""

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Schema for user response."""

    id: str
    email: str
    username: str
    role: str
    settings: dict = {}

    model_config = {"from_attributes": True}


class UserProfileUpdate(BaseModel):
    """Schema for updating user profile and settings."""

    username: str | None = Field(None, min_length=3, max_length=100)
    email: EmailStr | None = None
    password: str | None = Field(None, min_length=8, max_length=100)
    settings: dict | None = None


class TokenResponse(BaseModel):
    """Schema for token response."""

    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenRefresh(BaseModel):
    """Schema for token refresh."""

    refresh_token: str


class TokenWithRefreshResponse(BaseModel):
    """Schema for token refresh response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class ResetRequestCreate(BaseModel):
    """Schema for submitting a password reset request."""

    email: EmailStr
    username: str | None = Field(None, max_length=100)
    reason: str | None = Field(None, max_length=500)


class ResetRequestResponse(BaseModel):
    """Schema for returning a reset request."""

    id: str
    email: str
    username: str | None
    reason: str | None
    status: str
    created_at: str | None = None

    model_config = {"from_attributes": True}

