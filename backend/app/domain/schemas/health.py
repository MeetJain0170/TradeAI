"""Health endpoint response schemas."""

from typing import Literal

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response returned by GET /health."""

    status: Literal["ok"] = Field(
        default="ok",
        description="Service health status.",
        json_schema_extra={"example": "ok"},
    )
