"""User ORM model."""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base_model import BaseModel


class User(BaseModel):
    """User entity mapping to the ``users`` table.

    Attributes
    ----------
    email:
        Unique email address used for login.
    hashed_password:
        Bcrypt/Argon2 password hash.  Never returned in API responses.
    full_name:
        User's display name.
    is_active:
        Account status flag.  Inactive users cannot log in.
    is_superuser:
        Administrative privilege flag.
    """

    __tablename__ = "users"

    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )

    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    full_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    is_superuser: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
