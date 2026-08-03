"""AuditLog Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AuditLogBase(BaseModel):
    """Base AuditLog fields."""

    action: str = Field(description="Action identifier.")
    resource_type: str = Field(description="Affected resource type.")
    resource_id: str | None = Field(default=None, description="Affected resource ID.")
    details: dict[str, Any] | None = Field(
        default=None, description="Action detail payload."
    )
    ip_address: str | None = Field(default=None, description="Client IP address.")


class AuditLogCreate(AuditLogBase):
    """Schema for creating an audit log entry."""

    user_id: UUID | None = Field(
        default=None, description="User UUID performing the action."
    )


class AuditLogResponse(AuditLogBase):
    """Schema for returning audit log details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="Audit log entry UUID.")
    user_id: UUID | None = Field(
        default=None, description="User UUID performing the action."
    )
    created_at: datetime = Field(description="Creation UTC timestamp.")
    updated_at: datetime = Field(description="Last update UTC timestamp.")
    deleted_at: datetime | None = Field(
        default=None, description="Soft delete UTC timestamp."
    )
