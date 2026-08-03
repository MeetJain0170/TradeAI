"""JWT creation, decoding, and verification service using PyJWT."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import jwt
from config.settings import get_settings
from jwt.exceptions import PyJWTError

from app.core.exceptions import AuthenticationError


class JWTService:
    """Service handling JWT access and refresh token creation and verification."""

    @classmethod
    def create_access_token(
        cls,
        user_id: UUID | str,
        email: str,
        role: str = "TRADER",
        expires_delta: timedelta | None = None,
    ) -> tuple[str, str]:
        """Create a signed JWT access token with unique JTI.

        Returns
        -------
        tuple[str, str]
            (token_string, jti)
        """
        settings = get_settings()
        jti = str(uuid4())
        now = datetime.now(UTC)

        lifetime = (
            expires_delta
            if expires_delta is not None
            else timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        expire = now + lifetime

        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "jti": jti,
            "token_type": "access",
        }

        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithm=settings.JWT_ALGORITHM,
        )
        return token, jti

    @classmethod
    def create_refresh_token(
        cls,
        user_id: UUID | str,
        email: str,
        role: str = "TRADER",
        expires_delta: timedelta | None = None,
    ) -> tuple[str, str]:
        """Create a signed JWT refresh token with unique JTI.

        Returns
        -------
        tuple[str, str]
            (token_string, jti)
        """
        settings = get_settings()
        jti = str(uuid4())
        now = datetime.now(UTC)

        lifetime = (
            expires_delta
            if expires_delta is not None
            else timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)
        )
        expire = now + lifetime

        payload = {
            "sub": str(user_id),
            "email": email,
            "role": role,
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "jti": jti,
            "token_type": "refresh",
        }

        token = jwt.encode(
            payload,
            settings.JWT_SECRET_KEY.get_secret_value(),
            algorithm=settings.JWT_ALGORITHM,
        )
        return token, jti

    @classmethod
    def decode_token(cls, token: str) -> dict[str, Any]:
        """Decode and verify a JWT token signature and expiration.

        Raises
        ------
        AuthenticationError
            If token is invalid, malformed, or expired.
        """
        settings = get_settings()
        try:
            payload: dict[str, Any] = jwt.decode(
                token,
                settings.JWT_SECRET_KEY.get_secret_value(),
                algorithms=[settings.JWT_ALGORITHM],
            )
            return payload
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationError("Token has expired.") from exc
        except PyJWTError as exc:
            raise AuthenticationError(f"Invalid token: {exc}") from exc

    @classmethod
    def verify_token(cls, token: str, expected_type: str) -> dict[str, Any]:
        """Verify token and ensure it matches the expected token_type.

        Parameters
        ----------
        token:
            Encoded JWT token.
        expected_type:
            Expected token type string ("access" or "refresh").

        Returns
        -------
        dict[str, Any]
            Decoded token claims payload.
        """
        payload = cls.decode_token(token)
        token_type = payload.get("token_type")

        if token_type != expected_type:
            raise AuthenticationError(
                f"Invalid token type: expected '{expected_type}', got '{token_type}'."
            )
        return payload
