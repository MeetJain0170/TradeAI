"""Pydantic schemas for Market Data domain and API models."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class QuoteResponse(BaseModel):
    """Normalized real-time quote payload."""

    model_config = ConfigDict(from_attributes=True)

    symbol: str = Field(description="Canonical symbol (e.g., AAPL).")
    price: Decimal = Field(description="Current market price.")
    open: Decimal | None = Field(default=None, description="Day opening price.")
    high: Decimal | None = Field(default=None, description="Day high price.")
    low: Decimal | None = Field(default=None, description="Day low price.")
    prev_close: Decimal | None = Field(
        default=None, description="Previous close price."
    )
    volume: int | None = Field(default=None, description="Trading volume.")
    currency: str | None = Field(default=None, description="Currency.")
    exchange: str | None = Field(default=None, description="Exchange.")
    name: str | None = Field(default=None, description="Instrument name.")
    provider: str = Field(description="Data provider name (e.g. yahoo).")
    provider_symbol: str = Field(description="Provider-specific symbol code.")
    fetched_at: datetime = Field(description="Timestamp when quote was fetched.")


class OHLCVBar(BaseModel):
    """Single OHLCV historical candle."""

    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime = Field(description="Candle timestamp (UTC).")
    open: Decimal = Field(description="Opening price.")
    high: Decimal = Field(description="High price.")
    low: Decimal = Field(description="Low price.")
    close: Decimal = Field(description="Closing price.")
    volume: int = Field(description="Volume.")
    interval: str = Field(description="Time interval (e.g., 1d, 1h).")
    provider: str = Field(description="Provider name.")
    provider_symbol: str = Field(description="Provider-specific symbol code.")


class HistoryResponse(BaseModel):
    """Historical OHLCV response container."""

    symbol: str = Field(description="Canonical symbol.")
    interval: str = Field(description="Candle interval.")
    period: str = Field(description="Requested period string.")
    count: int = Field(description="Number of bars returned.")
    bars: list[OHLCVBar] = Field(
        default_factory=list, description="List of OHLCV candles."
    )


class IndexItem(BaseModel):
    """Single market index status item."""

    symbol: str = Field(description="Index symbol (e.g., ^GSPC).")
    name: str = Field(description="Index display name.")
    price: Decimal = Field(description="Current index value.")
    change: Decimal | None = Field(default=None, description="Absolute change.")
    change_pct: Decimal | None = Field(default=None, description="Percentage change.")
    provider: str = Field(description="Provider name.")
    provider_symbol: str = Field(description="Provider-specific symbol code.")


class IndicesResponse(BaseModel):
    """Response payload for market indices."""

    indices: list[IndexItem] = Field(
        default_factory=list, description="List of market indices."
    )


class OptionItem(BaseModel):
    """Single option contract details."""

    symbol: str = Field(description="Option contract symbol.")
    expiry: date = Field(description="Expiration date.")
    strike: Decimal = Field(description="Strike price.")
    option_type: str = Field(description="Contract type: call or put.")
    last_price: Decimal | None = Field(default=None, description="Last traded price.")
    volume: int | None = Field(default=None, description="Trading volume.")
    open_interest: int | None = Field(default=None, description="Open interest.")
    provider: str = Field(description="Provider name.")
    provider_symbol: str = Field(description="Provider symbol code.")


class OptionsResponse(BaseModel):
    """Response payload for options chain."""

    symbol: str = Field(description="Underlying asset symbol.")
    count: int = Field(description="Total option contracts returned.")
    provider_note: str | None = Field(
        default=None,
        description="Note regarding provider data availability or limitations.",
    )
    options: list[OptionItem] = Field(
        default_factory=list, description="List of option contracts."
    )
