"""Yahoo Finance implementation of BaseMarketDataProvider.

This provider delegates calls to ``YahooFinanceClient`` running inside thread executors
(via ``asyncio.to_thread``) to prevent blocking the async loop.
"""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime
from decimal import Decimal

from external.yahoo_finance.client import YahooFinanceClient

from app.core.exceptions import InfrastructureError
from app.services.market_data.providers.base import BaseMarketDataProvider
from app.services.market_data.types import (
    ProviderHealth,
    RawIndex,
    RawOHLCV,
    RawOption,
    RawQuote,
)


class YahooFinanceProvider(BaseMarketDataProvider):
    """Concrete Market Data Provider using Yahoo Finance."""

    PROVIDER_NAME = "yahoo"

    def __init__(self, client: YahooFinanceClient | None = None) -> None:
        self.client = client or YahooFinanceClient()

    async def initialize(self) -> None:
        """Initialize provider connections."""
        pass

    async def shutdown(self) -> None:
        """Clean up provider resources."""
        pass

    async def health_check(self) -> ProviderHealth:
        """Ping provider with a lightweight query and measure latency."""
        start = time.perf_counter()
        now = datetime.now(UTC)
        try:
            # Query AAPL quote as health check probe
            await asyncio.to_thread(self.client.fetch_quote, "AAPL")
            latency = (time.perf_counter() - start) * 1000.0
            return ProviderHealth(
                healthy=True,
                provider=self.PROVIDER_NAME,
                latency_ms=round(latency, 2),
                checked_at=now,
            )
        except Exception as exc:
            latency = (time.perf_counter() - start) * 1000.0
            return ProviderHealth(
                healthy=False,
                provider=self.PROVIDER_NAME,
                latency_ms=round(latency, 2),
                checked_at=now,
                error=str(exc),
            )

    async def get_quote(self, symbol: str) -> RawQuote:
        """Fetch raw current quote for symbol."""
        try:
            data = await asyncio.to_thread(self.client.fetch_quote, symbol)
            return RawQuote(
                symbol=symbol.upper(),
                price=Decimal(str(data["price"])),
                open=Decimal(str(data["open"])) if data["open"] is not None else None,
                high=Decimal(str(data["high"])) if data["high"] is not None else None,
                low=Decimal(str(data["low"])) if data["low"] is not None else None,
                prev_close=Decimal(str(data["prev_close"]))
                if data["prev_close"] is not None
                else None,
                volume=data["volume"],
                currency=data["currency"],
                exchange=data["exchange"],
                name=data["name"],
                provider=self.PROVIDER_NAME,
                provider_symbol=data["provider_symbol"],
                fetched_at=data["fetched_at"],
            )
        except Exception as exc:
            raise InfrastructureError(
                f"YahooFinance get_quote failed for {symbol}: {exc}"
            ) from exc

    async def get_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> list[RawOHLCV]:
        """Fetch raw historical OHLCV bars for symbol."""
        try:
            bars_data = await asyncio.to_thread(
                self.client.fetch_history, symbol, period, interval
            )
            raw_bars: list[RawOHLCV] = []
            for b in bars_data:
                raw_bars.append(
                    RawOHLCV(
                        symbol=symbol.upper(),
                        timestamp=b["timestamp"],
                        interval=interval,
                        open=Decimal(str(b["open"])),
                        high=Decimal(str(b["high"])),
                        low=Decimal(str(b["low"])),
                        close=Decimal(str(b["close"])),
                        volume=b["volume"],
                        provider=self.PROVIDER_NAME,
                        provider_symbol=b["provider_symbol"],
                    )
                )
            return raw_bars
        except Exception as exc:
            raise InfrastructureError(
                f"YahooFinance get_history failed for {symbol}: {exc}"
            ) from exc

    async def get_indices(self) -> list[RawIndex]:
        """Fetch raw major market indices status."""
        try:
            indices_data = await asyncio.to_thread(self.client.fetch_indices)
            raw_indices: list[RawIndex] = []
            for idx in indices_data:
                raw_indices.append(
                    RawIndex(
                        symbol=idx["symbol"],
                        name=idx["name"],
                        price=Decimal(str(idx["price"])),
                        change=Decimal(str(idx["change"]))
                        if idx["change"] is not None
                        else None,
                        change_pct=Decimal(str(idx["change_pct"]))
                        if idx["change_pct"] is not None
                        else None,
                        provider=self.PROVIDER_NAME,
                        provider_symbol=idx["provider_symbol"],
                    )
                )
            return raw_indices
        except Exception as exc:
            raise InfrastructureError(
                f"YahooFinance get_indices failed: {exc}"
            ) from exc

    async def get_options_chain(
        self,
        symbol: str,
    ) -> tuple[list[RawOption], str | None]:
        """Fetch raw options chain contracts and provider note."""
        try:
            res = await asyncio.to_thread(self.client.fetch_options_chain, symbol)
            raw_options: list[RawOption] = []
            for opt in res["options"]:
                raw_options.append(
                    RawOption(
                        symbol=opt["symbol"],
                        expiry=opt["expiry"],
                        strike=Decimal(str(opt["strike"])),
                        option_type=opt["option_type"],
                        last_price=Decimal(str(opt["last_price"]))
                        if opt["last_price"] is not None
                        else None,
                        volume=opt["volume"],
                        open_interest=opt["open_interest"],
                        provider=self.PROVIDER_NAME,
                        provider_symbol=opt["provider_symbol"],
                    )
                )
            return raw_options, res["provider_note"]
        except Exception as exc:
            raise InfrastructureError(
                f"YahooFinance get_options_chain failed for {symbol}: {exc}"
            ) from exc
