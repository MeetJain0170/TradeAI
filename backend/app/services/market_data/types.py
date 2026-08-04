"""Data transfer types for Market Data providers and service layers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass
class RawQuote:
    """Raw quote returned from a provider prior to normalization."""

    symbol: str
    price: Decimal
    open: Decimal | None
    high: Decimal | None
    low: Decimal | None
    prev_close: Decimal | None
    volume: int | None
    currency: str | None
    exchange: str | None
    name: str | None
    provider: str
    provider_symbol: str
    fetched_at: datetime


@dataclass
class RawOHLCV:
    """Raw OHLCV bar returned from a provider prior to normalization/validation."""

    symbol: str
    timestamp: datetime
    interval: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int
    provider: str
    provider_symbol: str


@dataclass
class RawOption:
    """Raw option contract returned from a provider."""

    symbol: str
    expiry: date
    strike: Decimal
    option_type: str  # "call" | "put"
    last_price: Decimal | None
    volume: int | None
    open_interest: int | None
    provider: str
    provider_symbol: str


@dataclass
class RawIndex:
    """Raw market index status returned from a provider."""

    symbol: str
    name: str
    price: Decimal
    change: Decimal | None
    change_pct: Decimal | None
    provider: str
    provider_symbol: str


@dataclass
class ProviderHealth:
    """Detailed health check status for a market data provider."""

    healthy: bool
    provider: str
    latency_ms: float
    checked_at: datetime
    error: str | None = None
