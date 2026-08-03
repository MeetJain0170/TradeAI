"""SystemLog ORM model."""

from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.database.models.base_model import BaseModel


class SystemLog(BaseModel):
    """SystemLog entity mapping to the ``system_logs`` table.

    Stores system events, warnings, errors, and background task outputs.

    Attributes
    ----------
    level:
        Log level string ("INFO", "WARNING", "ERROR", "CRITICAL").
    message:
        Main log message text.
    module:
        Module name where the log originated.
    request_id:
        Correlation request ID context.
    stack_trace:
        Full exception stack trace if applicable.
    """

    __tablename__ = "system_logs"

    level: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    module: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
    )

    request_id: Mapped[str | None] = mapped_column(
        String(36),
        nullable=True,
        index=True,
    )

    stack_trace: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
