"""
FastAPI dependency injection for database sessions,
authentication, RBAC, and rate limiting.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, AuthorizationError
from app.infrastructure.database.models.user import User
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.database.session import get_db_session
from app.infrastructure.redis.client import check_rate_limit
from app.security.jwt import JWTService
from app.security.roles import Role, has_sufficient_role
from app.services.auth_service import AuthService
from app.services.market_data.service import MarketDataService

security_bearer = HTTPBearer(auto_error=False)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Yield an AsyncSession for the current request."""
    async for session in get_db_session():
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


def get_user_repository(session: DbSession) -> UserRepository:
    """Provide a UserRepository instance."""
    return UserRepository(session)


UserRepositoryDep = Annotated[
    UserRepository,
    Depends(get_user_repository),
]


def get_auth_service(session: DbSession) -> AuthService:
    """Provide an AuthService instance."""
    return AuthService(session)


AuthServiceDep = Annotated[
    AuthService,
    Depends(get_auth_service),
]


def get_market_data_service(session: DbSession) -> MarketDataService:
    """Provide a MarketDataService instance."""
    return MarketDataService(session)


MarketDataServiceDep = Annotated[
    MarketDataService,
    Depends(get_market_data_service),
]


# --------------------------------------------------------------------------- #
# Authentication Dependencies
# --------------------------------------------------------------------------- #


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(security_bearer),
    ],
    session: DbSession,
) -> User:
    """
    Authenticate a Bearer access token and return the current user.

    Raises:
        AuthenticationError: If the Authorization header is missing,
        the token is invalid or expired, or the user no longer exists.
    """
    if credentials is None or not credentials.credentials:
        raise AuthenticationError(
            "Missing Authorization Bearer header.",
            http_status=401,
        )

    token = credentials.credentials
    payload = JWTService.verify_token(token, "access")
    sub = payload.get("sub")

    if not sub:
        raise AuthenticationError(
            "Invalid token payload: missing subject.",
        )

    user_repo = UserRepository(session)
    user = await user_repo.get_by_id(UUID(sub))

    if user is None:
        raise AuthenticationError(
            "User associated with this token no longer exists.",
        )

    return user


CurrentUserDep = Annotated[
    User,
    Depends(get_current_user),
]


async def get_current_active_user(
    user: CurrentUserDep,
) -> User:
    """Ensure the authenticated user account is active."""
    if not user.is_active:
        raise AuthenticationError("User account is inactive.")
    return user


CurrentActiveUserDep = Annotated[
    User,
    Depends(get_current_active_user),
]


# --------------------------------------------------------------------------- #
# Authorization (RBAC) Dependency
# --------------------------------------------------------------------------- #


class RoleChecker:
    """Dependency enforcing Role-Based Access Control."""

    def __init__(
        self,
        allowed_roles: list[Role | str],
    ) -> None:
        self.allowed_roles = [
            Role(role) if isinstance(role, str) else role for role in allowed_roles
        ]

    async def __call__(
        self,
        user: CurrentActiveUserDep,
    ) -> User:
        """Verify that the authenticated user has sufficient permissions."""
        user_role = Role(user.role)

        for required_role in self.allowed_roles:
            if has_sufficient_role(user_role, required_role):
                return user

        raise AuthorizationError(
            (f"Role '{user_role.value}' is not authorized to access this resource."),
            http_status=403,
        )


# --------------------------------------------------------------------------- #
# Rate Limiting Dependency
# --------------------------------------------------------------------------- #


class RateLimiter:
    """Redis-backed sliding-window rate limiter."""

    def __init__(
        self,
        requests_per_window: int = 100,
        window_seconds: int = 60,
    ) -> None:
        self.requests_per_window = requests_per_window
        self.window_seconds = window_seconds

    async def __call__(
        self,
        request: Request,
    ) -> None:
        """Validate request rate limits."""

        client_identifier = request.client.host if request.client else "unknown"

        endpoint_key = f"{request.method}:{request.url.path}"
        key = f"{client_identifier}:{endpoint_key}"

        is_allowed, remaining = await check_rate_limit(
            key,
            self.requests_per_window,
            self.window_seconds,
        )

        if not is_allowed:
            raise AuthenticationError(
                (
                    "Rate limit exceeded. Maximum "
                    f"{self.requests_per_window} requests "
                    f"per {self.window_seconds} seconds."
                ),
                http_status=429,
                code="RATE_LIMIT_EXCEEDED",
            )
