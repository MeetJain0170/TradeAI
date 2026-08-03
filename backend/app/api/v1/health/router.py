"""Health check API router for v1."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.envelope import SuccessResponse, success_response
from app.domain.schemas.health import HealthResponse

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    response_model=SuccessResponse[HealthResponse],
    status_code=status.HTTP_200_OK,
    summary="Health check endpoint",
)
async def health_check_v1() -> SuccessResponse[HealthResponse]:
    """Return application health status wrapped 
    userin standardized SuccessResponse envelope."""
    payload = HealthResponse(status="ok")
    return success_response(payload)
