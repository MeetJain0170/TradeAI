"""Unit tests for PasswordService."""

from __future__ import annotations

import pytest
from app.core.exceptions import ValidationError
from app.security.password import PasswordService


def test_hash_and_verify_password() -> None:
    """Verify password hashing and verification match."""
    password = "ValidPassword123!"
    hashed = PasswordService.hash_password(password)
    assert hashed != password
    assert PasswordService.verify_password(password, hashed) is True
    assert PasswordService.verify_password("WrongPassword123!", hashed) is False


def test_validate_password_strength_success() -> None:
    """Verify valid password passes strength policy."""
    valid_passwords = [
        "Str0ngPass!",
        "Complex#2026Password",
        "P@ssw0rd123",
    ]
    for pwd in valid_passwords:
        # Should not raise exception
        PasswordService.validate_password_strength(pwd)


def test_validate_password_strength_failures() -> None:
    """Verify weak passwords fail policy with ValidationError."""
    with pytest.raises(ValidationError, match="at least 8 characters"):
        PasswordService.validate_password_strength("Short1!")

    with pytest.raises(ValidationError, match="uppercase letter"):
        PasswordService.validate_password_strength("lowercase123!")

    with pytest.raises(ValidationError, match="lowercase letter"):
        PasswordService.validate_password_strength("UPPERCASE123!")

    with pytest.raises(ValidationError, match="numeric digit"):
        PasswordService.validate_password_strength("NoDigitsHere!")

    with pytest.raises(ValidationError, match="special character"):
        PasswordService.validate_password_strength("NoSpecialChar123")
