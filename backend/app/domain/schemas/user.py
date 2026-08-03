"""User Pydantic schemas (Phase 2: persistence layer).

Authentication-related schemas (``UserLoginRequest``, tokens) are
introduced in Phase 3 — Authentication.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    """Base fields shared across User schemas."""

    email: EmailStr = Field(description="Unique email address.")
    full_name: str | None = Field(default=None, description="User full name.")
    is_active: bool = Field(default=True, description="Account active status.")
    is_superuser: bool = Field(default=False, description="Superuser status.")


class UserCreate(UserBase):
    """Schema for user creation."""

    password: str = Field(min_length=8, description="User password (min 8 chars).")


class UserUpdate(BaseModel):
    """Schema for updating user details."""

    email: EmailStr | None = Field(default=None, description="Updated email address.")
    full_name: str | None = Field(default=None, description="Updated full name.")
    password: str | None = Field(
        default=None, min_length=8, description="Updated password."
    )
    is_active: bool | None = Field(default=None, description="Updated active status.")
    is_superuser: bool | None = Field(
        default=None, description="Updated superuser status."
    )


class UserResponse(UserBase):
    """Public user response schema. Never exposes sensitive fields."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Unique user UUID.")
    created_at: datetime = Field(description="Creation UTC timestamp.")
    updated_at: datetime = Field(description="Last update UTC timestamp.")
    deleted_at: datetime | None = Field(
        default=None, description="Soft delete UTC timestamp."
    )


class UserListResponse(BaseModel):
    """Paginated list of users response."""

    items: list[UserResponse] = Field(description="List of user items.")
    total_count: int = Field(ge=0, description="Total matching records count.")
    page: int = Field(ge=1, description="Current page number.")
    page_size: int = Field(ge=1, description="Number of items per page.")
    total_pages: int = Field(ge=0, description="Total available pages count.")
