"""Standardized API response envelope models."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    """Standardized API success envelope model."""

    success: bool = Field(default=True, description="Success status flag.")
    data: T = Field(description="Payload data.")
    meta: dict[str, Any] | None = Field(
        default=None, description="Optional response metadata."
    )


def success_response(
    data: Any, meta: dict[str, Any] | None = None
) -> SuccessResponse[Any]:
    """Helper function to construct a SuccessResponse envelope."""
    return SuccessResponse(success=True, data=data, meta=meta)
