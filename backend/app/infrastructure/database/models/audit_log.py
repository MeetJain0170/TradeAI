"""AuditLog ORM model."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base_model import BaseModel


class AuditLog(BaseModel):
    """AuditLog entity mapping to the ``audit_logs`` table.

    Records security-relevant user actions (login, trade submission, settings change).

    Attributes
    ----------
    user_id:
        UUID of the user who performed the action (nullable).
    action:
        Action identifier (e.g., "user_login", "trade_submitted").
    resource_type:
        Affected entity type (e.g., "user", "trade", "portfolio").
    resource_id:
        Identifier of the affected resource.
    details:
        Arbitrary JSON payload containing contextual parameters.
    ip_address:
        IP address of the client triggering the action.
    """

    __tablename__ = "audit_logs"

    user_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    action: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )

    resource_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    resource_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    details: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    ip_address: Mapped[str | None] = mapped_column(
        String(45),
        nullable=True,
    )
