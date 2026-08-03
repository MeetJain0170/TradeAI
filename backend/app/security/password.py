"""Password management service: hashing, verification, and policy enforcement."""

from __future__ import annotations

import re

import bcrypt

from app.core.exceptions import ValidationError


class PasswordService:
    """Service providing secure bcrypt hashing and password policy validation."""

    SPECIAL_CHARACTERS = r"!@#$%^&*()_+-=[]{}|;:,.<>?"

    @staticmethod
    def hash_password(plain_password: str) -> str:
        """Hash a plain text password using bcrypt.

        Parameters
        ----------
        plain_password:
            The raw password string.

        Returns
        -------
        str
            Bcrypt hashed password string.
        """
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain text password against a stored bcrypt hash.

        Parameters
        ----------
        plain_password:
            The raw password to check.
        hashed_password:
            The stored bcrypt password hash.

        Returns
        -------
        bool
            True if password matches, False otherwise.
        """
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except (ValueError, TypeError):
            return False

    @classmethod
    def validate_password_strength(cls, password: str) -> None:
        """Enforce strict enterprise password policy requirements.

        Policy rules:
        - Minimum 8 characters long
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one numeric digit
        - At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

        Raises
        ------
        ValidationError
            If the password fails any policy rule.
        """
        if len(password) < 8:
            raise ValidationError(
                "Password must be at least 8 characters long.",
                details={"field": "password", "rule": "min_length"},
            )

        if not re.search(r"[A-Z]", password):
            raise ValidationError(
                "Password must contain at least one uppercase letter.",
                details={"field": "password", "rule": "uppercase_required"},
            )

        if not re.search(r"[a-z]", password):
            raise ValidationError(
                "Password must contain at least one lowercase letter.",
                details={"field": "password", "rule": "lowercase_required"},
            )

        if not re.search(r"\d", password):
            raise ValidationError(
                "Password must contain at least one numeric digit.",
                details={"field": "password", "rule": "digit_required"},
            )

        pattern = f"[{re.escape(cls.SPECIAL_CHARACTERS)}]"
        if not re.search(pattern, password):
            raise ValidationError(
                f"Password must contain at least one special character "
                f"({cls.SPECIAL_CHARACTERS}).",
                details={"field": "password", "rule": "special_char_required"},
            )
