"""SystemLog Pydantic schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SystemLogBase(BaseModel):
    """Base SystemLog fields."""

    level: str = Field(description="Log severity level.")
    message: str = Field(description="Log text message.")
    module: str | None = Field(default=None, description="Source module name.")
    request_id: str | None = Field(default=None, description="Context request ID.")
    stack_trace: str | None = Field(
        default=None, description="Exception stack trace text."
    )


class SystemLogCreate(SystemLogBase):
    """Schema for creating a system log entry."""

    pass


class SystemLogResponse(SystemLogBase):
    """Schema for returning system log details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(description="System log entry UUID.")
    created_at: datetime = Field(description="Creation UTC timestamp.")
    updated_at: datetime = Field(description="Last update UTC timestamp.")
    deleted_at: datetime | None = Field(
        default=None, description="Soft delete UTC timestamp."
    )
