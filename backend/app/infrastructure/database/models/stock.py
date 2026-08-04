"""Stock ORM model — metadata row per tracked equity or instrument."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.infrastructure.database.models.market_data import MarketData

from app.infrastructure.database.models.base_model import BaseModel


class Stock(BaseModel):
    """Stock entity mapping to the ``stocks`` table.

    One row per unique instrument.  The ``symbol`` is the canonical
    application-level identifier (e.g. ``AAPL``, ``RELIANCE.NS``).
    Provider-specific symbol mappings are stored per-row in ``market_data``.
    """

    __tablename__ = "stocks"

    symbol: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    exchange: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )
    currency: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
    )
    sector: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    industry: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Relationship to OHLCV rows (lazy-loaded by default)
    market_data: Mapped[list[MarketData]] = relationship(
        "MarketData",
        back_populates="stock",
        lazy="select",
    )
