"""Abstract BaseModel with standard columns (id, created_at, updated_at, deleted_at)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.base import Base


class BaseModel(Base):
    """Abstract base model introducing UUID primary key, timestamps, and soft delete.

    Attributes
    ----------
    id:
        UUID primary key (defaults to uuid4).
    created_at:
        Time of record creation in UTC.
    updated_at:
        Time of last record modification in UTC.
    deleted_at:
        Soft-delete timestamp in UTC (None when active).
    """

    __abstract__ = True

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        default=None,
        index=True,
    )

    @property
    def is_deleted(self) -> bool:
        """Return True if this entity has been soft-deleted."""
        return self.deleted_at is not None
