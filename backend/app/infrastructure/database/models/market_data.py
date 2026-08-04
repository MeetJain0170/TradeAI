"""MarketData ORM model — OHLCV candles for all tracked instruments."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from app.infrastructure.database.models.stock import Stock

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.models.base_model import BaseModel


class MarketData(BaseModel):
    """OHLCV candle entity mapping to the ``market_data`` table.

    The ``(stock_id, timestamp, interval)`` triple is unique — duplicate
    candles are silently ignored by ``bulk_upsert`` via ON CONFLICT DO NOTHING.

    Notes
    -----
    * ``updated_at`` and ``deleted_at`` are inherited from BaseModel but
      semantically unused for append-only candle rows.
    * Prices use ``DECIMAL(20, 8)`` to correctly represent crypto, forex,
      and futures values without precision loss.
    * ``provider_symbol`` stores what the provider called this instrument
      (e.g. Yahoo uses ``AAPL`` while Upstox uses ``NSE_EQ|INE002A01018``).
    """

    __tablename__ = "market_data"
    __table_args__ = (
        UniqueConstraint(
            "stock_id",
            "timestamp",
            "interval",
            name="uq_market_data_stock_timestamp_interval",
        ),
    )

    stock_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("stocks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    interval: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        comment="Candle interval: 1m | 5m | 15m | 30m | 1h | 4h | 1d | 1wk",
    )

    # OHLCV — DECIMAL(20, 8) supports crypto/forex/futures precision
    open: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    high: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    low: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    close: Mapped[Decimal | None] = mapped_column(Numeric(20, 8), nullable=True)
    volume: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    # Provider metadata
    provider: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Provider name: yahoo | upstox | zerodha | polygon",
    )
    provider_symbol: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment=(
            "Symbol as used by the provider "
            "(may differ from the canonical application symbol)"
        ),
    )

    # Relationship
    stock: Mapped[Stock] = relationship(
        "Stock",
        back_populates="market_data",
        lazy="select",
    )
