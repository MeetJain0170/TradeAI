"""Authentication API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.dependencies import (
    AuthServiceDep,
    CurrentActiveUserDep,
    RateLimiter,
)
from app.api.envelope import SuccessResponse, success_response
from app.domain.schemas.user import (
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])

login_rate_limiter = RateLimiter(requests_per_window=5, window_seconds=60)
standard_rate_limiter = RateLimiter(requests_per_window=100, window_seconds=60)


@router.post(
    "/register",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    dependencies=[Depends(standard_rate_limiter)],
)
async def register(
    request: UserRegisterRequest,
    auth_service: AuthServiceDep,
) -> SuccessResponse[UserResponse]:
    """Register a new user account with normalized
    email and password strength validation."""
    user = await auth_service.register(request)
    return success_response(user)


@router.post(
    "/login",
    response_model=SuccessResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Authenticate credentials and return JWT token pair",
    dependencies=[Depends(login_rate_limiter)],
)
async def login(
    request: UserLoginRequest,
    auth_service: AuthServiceDep,
) -> SuccessResponse[TokenResponse]:
    """
    Authenticate user with email and password, 
    returning Access + Refresh JWT tokens.
    """
    tokens = await auth_service.login(request.email, request.password)
    return success_response(tokens)


@router.post(
    "/logout",
    response_model=SuccessResponse[dict[str, str]],
    status_code=status.HTTP_200_OK,
    summary="Revoke refresh token and log out user",
    dependencies=[Depends(standard_rate_limiter)],
)
async def logout(
    request: RefreshTokenRequest,
    auth_service: AuthServiceDep,
) -> SuccessResponse[dict[str, str]]:
    """Revoke the provided Refresh Token JTI in Redis."""
    await auth_service.logout(request.refresh_token)
    return success_response({"message": "Successfully logged out."})


@router.post(
    "/refresh",
    response_model=SuccessResponse[TokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Exchange refresh token for new access and refresh token pair",
    dependencies=[Depends(standard_rate_limiter)],
)
async def refresh(
    request: RefreshTokenRequest,
    auth_service: AuthServiceDep,
) -> SuccessResponse[TokenResponse]:
    """Perform token rotation by validating refresh token, 
    revoking old JTI, and issuing new pair."""
    tokens = await auth_service.refresh(request.refresh_token)
    return success_response(tokens)


@router.get(
    "/profile",
    response_model=SuccessResponse[UserResponse],
    status_code=status.HTTP_200_OK,
    summary="Fetch current authenticated user profile",
    dependencies=[Depends(standard_rate_limiter)],
)
async def get_profile(
    current_user: CurrentActiveUserDep,
) -> SuccessResponse[UserResponse]:
    """Fetch user profile details for the 
    currently authenticated Bearer token user."""
    return success_response(UserResponse.model_validate(current_user))
