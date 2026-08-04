"""Abstract base class interface for all Market Data providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.services.market_data.types import (
    ProviderHealth,
    RawIndex,
    RawOHLCV,
    RawOption,
    RawQuote,
)


class BaseMarketDataProvider(ABC):
    """Abstract market data provider interface.

    Every concrete market data source (Yahoo Finance, Upstox, Zerodha, Polygon)
    must subclass this interface.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize provider connections or state."""
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        """Clean up provider resources."""
        ...

    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        """Perform provider health check and return ProviderHealth status."""
        ...

    @abstractmethod
    async def get_quote(self, symbol: str) -> RawQuote:
        """Fetch current real-time quote for symbol."""
        ...

    @abstractmethod
    async def get_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[RawOHLCV]:
        """Fetch historical OHLCV bars for symbol."""
        ...

    @abstractmethod
    async def get_indices(self) -> list[RawIndex]:
        """Fetch status for supported major market indices."""
        ...

    @abstractmethod
    async def get_options_chain(
        self,
        symbol: str,
    ) -> tuple[list[RawOption], str | None]:
        """Fetch options chain contracts and optional provider note for symbol."""
        ...
