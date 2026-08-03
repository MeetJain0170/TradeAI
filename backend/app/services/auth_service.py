"""AuthService: registration, login, logout, token refresh, and profile logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from config.settings import get_settings
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ValidationError
from app.domain.schemas.user import (
    TokenResponse,
    UserCreate,
    UserRegisterRequest,
    UserResponse,
)
from app.infrastructure.database.models.user import User
from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.redis.client import (
    is_jti_revoked,
    revoke_jti,
    store_refresh_jti,
)
from app.security.jwt import JWTService
from app.security.password import PasswordService
from app.security.roles import Role


class AuthService:
    """Orchestrates authentication, password hashing, JWTs, and Redis JTI revocation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)

    async def register(self, request: UserRegisterRequest) -> UserResponse:
        """Register a new user account.

        Raises
        ------
        ValidationError
            If password confirmation fails, strength is weak, or email is duplicate.
        """
        if request.password != request.password_confirm:
            raise ValidationError(
                "Password confirmation does not match.",
                details={"field": "password_confirm"},
            )

        # Enforce password strength policy
        PasswordService.validate_password_strength(request.password)

        normalized_email = request.email.strip().lower()
        if await self.user_repo.email_exists(normalized_email):
            raise ValidationError(
                "An account with this email address already exists.",
                details={"field": "email", "rule": "unique"},
            )

        hashed_pw = PasswordService.hash_password(request.password)
        user_create = UserCreate(
            email=normalized_email,
            password=request.password,
            full_name=request.full_name,
        )

        user_orm = User(
            email=normalized_email,
            hashed_password=hashed_pw,
            full_name=user_create.full_name,
            role=Role.USER,
            is_active=True,
            is_superuser=False,
            is_verified=False,
        )
        created_user = await self.user_repo.create(user_orm)
        return UserResponse.model_validate(created_user)

    async def login(self, email: str, plain_password: str) -> TokenResponse:
        """Authenticate user credentials and return Access + Refresh JWT pair.

        Enforces 15-minute account lockout after 5 consecutive failed attempts.

        Raises
        ------
        AuthenticationError
            If credentials are invalid, account is inactive, or account is locked.
        """
        normalized_email = email.strip().lower()
        user = await self.user_repo.get_by_email(normalized_email)

        if user is None:
            raise AuthenticationError("Invalid email or password.")

        if not user.is_active:
            raise AuthenticationError("User account is inactive.")

        now = datetime.now(UTC)
        if user.locked_until is not None and user.locked_until > now:
            raise AuthenticationError(
                f"Account locked due to multiple failed login attempts "
                f"until {user.locked_until.isoformat()}."
            )

        if not PasswordService.verify_password(plain_password, user.hashed_password):
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= 5:
                user.locked_until = now + timedelta(minutes=15)
            await self.user_repo.update(user)
            raise AuthenticationError("Invalid email or password.")

        # Login successful — reset failed attempts & update last_login_at
        user.failed_login_attempts = 0
        user.locked_until = None
        user.last_login_at = now
        await self.user_repo.update(user)

        role = user.role if user.role else Role.USER
        access_token, _ = JWTService.create_access_token(
            user_id=user.id, email=user.email, role=role
        )
        refresh_token, refresh_jti = JWTService.create_refresh_token(
            user_id=user.id, email=user.email, role=role
        )

        settings = get_settings()
        refresh_expire_seconds = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400
        await store_refresh_jti(refresh_jti, str(user.id), refresh_expire_seconds)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def logout(self, refresh_token: str) -> None:
        """Revoke a refresh token JTI in Redis upon logout."""
        payload = JWTService.verify_token(refresh_token, "refresh")
        jti = payload.get("jti")
        if jti:
            await revoke_jti(jti)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        """Exchange a refresh token for a new Access + Refresh pair (token rotation)."""
        payload = JWTService.verify_token(refresh_token, "refresh")
        jti = payload.get("jti")
        sub = payload.get("sub")

        if not jti or not sub:
            raise AuthenticationError("Invalid refresh token payload.")

        if await is_jti_revoked(jti):
            raise AuthenticationError("Refresh token has been revoked or expired.")

        user = await self.user_repo.get_by_id(UUID(sub))
        if user is None or not user.is_active:
            raise AuthenticationError("User account no longer active.")

        # Revoke old JTI (token rotation)
        await revoke_jti(jti)

        role = user.role if user.role else Role.USER
        new_access, _ = JWTService.create_access_token(
            user_id=user.id, email=user.email, role=role
        )
        new_refresh, new_jti = JWTService.create_refresh_token(
            user_id=user.id, email=user.email, role=role
        )

        settings = get_settings()
        refresh_expire_seconds = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 86400
        await store_refresh_jti(new_jti, str(user.id), refresh_expire_seconds)

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            token_type="bearer",
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    async def get_user_profile(self, user_id: UUID) -> UserResponse:
        """Fetch UserResponse profile for authenticated user ID."""
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise AuthenticationError("User not found.")
        return UserResponse.model_validate(user)
