"""Unit tests for JWTService."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from app.core.exceptions import AuthenticationError
from app.security.jwt import JWTService


def test_create_and_decode_access_token() -> None:
    """Test creating and decoding a valid access token."""
    user_id = uuid4()
    email = "trader@example.com"
    token, jti = JWTService.create_access_token(user_id, email, role="TRADER")

    assert isinstance(token, str)
    assert len(jti) > 0

    payload = JWTService.verify_token(token, "access")
    assert payload["sub"] == str(user_id)
    assert payload["email"] == email
    assert payload["role"] == "TRADER"
    assert payload["token_type"] == "access"
    assert payload["jti"] == jti


def test_create_and_decode_refresh_token() -> None:
    """Test creating and decoding a valid refresh token."""
    user_id = uuid4()
    email = "trader@example.com"
    token, jti = JWTService.create_refresh_token(user_id, email, role="TRADER")

    payload = JWTService.verify_token(token, "refresh")
    assert payload["sub"] == str(user_id)
    assert payload["token_type"] == "refresh"
    assert payload["jti"] == jti


def test_token_type_mismatch() -> None:
    """Test verifying token with wrong expected_type raises AuthenticationError."""
    user_id = uuid4()
    token, _ = JWTService.create_access_token(user_id, "user@example.com")

    with pytest.raises(AuthenticationError, match="Invalid token type"):
        JWTService.verify_token(token, "refresh")


def test_expired_token() -> None:
    """Test decoding an expired token raises AuthenticationError."""
    user_id = uuid4()
    token, _ = JWTService.create_access_token(
        user_id, "user@example.com", expires_delta=timedelta(seconds=-10)
    )

    with pytest.raises(AuthenticationError, match="expired"):
        JWTService.decode_token(token)


def test_malformed_jwt() -> None:
    """Test decoding a malformed string raises AuthenticationError."""
    with pytest.raises(AuthenticationError, match="Invalid token"):
        JWTService.decode_token("not.a.valid.jwt")
