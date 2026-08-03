"""User Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.security.roles import Role


class UserBase(BaseModel):
    """Base fields shared across User schemas."""

    email: EmailStr = Field(description="Unique email address.")
    full_name: str | None = Field(
        default=None,
        description="User full name.",
    )
    role: Role = Field(
        default=Role.USER,
        description="User RBAC role.",
    )
    is_active: bool = Field(
        default=True,
        description="Account active status.",
    )
    is_superuser: bool = Field(
        default=False,
        description="Superuser status.",
    )
    is_verified: bool = Field(
        default=False,
        description="Account email verification status.",
    )


class UserCreate(UserBase):
    """Schema for user creation."""

    password: str = Field(
        min_length=8,
        description="User password.",
    )


class UserUpdate(BaseModel):
    """Schema for updating user details."""

    email: EmailStr | None = Field(
        default=None,
        description="Updated email address.",
    )
    full_name: str | None = Field(
        default=None,
        description="Updated full name.",
    )
    password: str | None = Field(
        default=None,
        min_length=8,
        description="Updated password.",
    )
    is_active: bool | None = Field(
        default=None,
        description="Updated active status.",
    )
    is_superuser: bool | None = Field(
        default=None,
        description="Updated superuser status.",
    )
    is_verified: bool | None = Field(
        default=None,
        description="Updated verification status.",
    )


class UserResponse(UserBase):
    """Public user response schema. Never exposes sensitive fields."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Unique user UUID.")
    last_login_at: datetime | None = Field(
        default=None,
        description="Last login timestamp.",
    )
    failed_login_attempts: int = Field(
        default=0,
        description="Failed login attempts count.",
    )
    locked_until: datetime | None = Field(
        default=None,
        description="Account lock expiration timestamp.",
    )
    created_at: datetime = Field(description="Creation UTC timestamp.")
    updated_at: datetime = Field(description="Last update UTC timestamp.")
    deleted_at: datetime | None = Field(
        default=None,
        description="Soft delete UTC timestamp.",
    )


class UserListResponse(BaseModel):
    """Paginated list of users response."""

    items: list[UserResponse] = Field(description="List of user items.")
    total_count: int = Field(
        ge=0,
        description="Total matching records count.",
    )
    page: int = Field(
        ge=1,
        description="Current page number.",
    )
    page_size: int = Field(
        ge=1,
        description="Number of items per page.",
    )
    total_pages: int = Field(
        ge=0,
        description="Total available pages count.",
    )


class UserRegisterRequest(BaseModel):
    """Schema for user registration."""

    email: EmailStr = Field(description="User email address.")
    password: str = Field(
        min_length=8,
        description="User password.",
    )
    password_confirm: str = Field(
        min_length=8,
        description="Password confirmation.",
    )
    full_name: str | None = Field(
        default=None,
        description="User full name.",
    )


class UserLoginRequest(BaseModel):
    """Schema for user login credentials."""

    email: EmailStr = Field(description="User login email.")
    password: str = Field(description="User login password.")


class TokenResponse(BaseModel):
    """JWT token pair response schema."""

    access_token: str = Field(description="JWT Access Token.")
    refresh_token: str = Field(description="JWT Refresh Token.")
    token_type: str = Field(
        default="bearer",
        description="Token type prefix.",
    )
    expires_in: int = Field(
        description="Access token lifetime in seconds.",
    )


class RefreshTokenRequest(BaseModel):
    """Schema for refreshing access tokens."""

    refresh_token: str = Field(
        description="JWT Refresh Token to exchange.",
    )