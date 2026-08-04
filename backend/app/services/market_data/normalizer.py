"""Pure functions for converting provider raw data into normalized Pydantic schemas."""

from __future__ import annotations

from app.domain.schemas.market_data import (
    HistoryResponse,
    IndexItem,
    IndicesResponse,
    OHLCVBar,
    OptionItem,
    OptionsResponse,
    QuoteResponse,
)
from app.services.market_data.types import (
    RawIndex,
    RawOHLCV,
    RawOption,
    RawQuote,
)


class MarketDataNormalizer:
    """Normalizer performing field transformation without I/O or validation
    side-effects.
    """

    @staticmethod
    def normalize_quote(raw: RawQuote) -> QuoteResponse:
        """Convert a RawQuote into a normalized QuoteResponse schema."""
        return QuoteResponse(
            symbol=raw.symbol.upper(),
            price=raw.price,
            open=raw.open,
            high=raw.high,
            low=raw.low,
            prev_close=raw.prev_close,
            volume=raw.volume,
            currency=raw.currency,
            exchange=raw.exchange,
            name=raw.name,
            provider=raw.provider,
            provider_symbol=raw.provider_symbol,
            fetched_at=raw.fetched_at,
        )

    @staticmethod
    def normalize_bar(raw: RawOHLCV) -> OHLCVBar:
        """Convert a single RawOHLCV into a normalized OHLCVBar schema."""
        return OHLCVBar(
            timestamp=raw.timestamp,
            open=raw.open,
            high=raw.high,
            low=raw.low,
            close=raw.close,
            volume=raw.volume,
            interval=raw.interval,
            provider=raw.provider,
            provider_symbol=raw.provider_symbol,
        )

    @classmethod
    def normalize_history(
        cls,
        symbol: str,
        period: str,
        interval: str,
        raw_bars: list[RawOHLCV],
    ) -> HistoryResponse:
        """Convert a list of RawOHLCV bars into a HistoryResponse payload."""
        bars = [cls.normalize_bar(b) for b in raw_bars]
        return HistoryResponse(
            symbol=symbol.upper(),
            interval=interval,
            period=period,
            count=len(bars),
            bars=bars,
        )

    @staticmethod
    def normalize_indices(raw_indices: list[RawIndex]) -> IndicesResponse:
        """Convert raw indices list into IndicesResponse payload."""
        items: list[IndexItem] = []
        for idx in raw_indices:
            items.append(
                IndexItem(
                    symbol=idx.symbol,
                    name=idx.name,
                    price=idx.price,
                    change=idx.change,
                    change_pct=idx.change_pct,
                    provider=idx.provider,
                    provider_symbol=idx.provider_symbol,
                )
            )
        return IndicesResponse(indices=items)

    @staticmethod
    def normalize_options(
        symbol: str,
        raw_options: list[RawOption],
        provider_note: str | None = None,
    ) -> OptionsResponse:
        """Convert raw options list into OptionsResponse payload."""
        items: list[OptionItem] = []
        for opt in raw_options:
            items.append(
                OptionItem(
                    symbol=opt.symbol,
                    expiry=opt.expiry,
                    strike=opt.strike,
                    option_type=opt.option_type,
                    last_price=opt.last_price,
                    volume=opt.volume,
                    open_interest=opt.open_interest,
                    provider=opt.provider,
                    provider_symbol=opt.provider_symbol,
                )
            )
        return OptionsResponse(
            symbol=symbol.upper(),
            count=len(items),
            provider_note=provider_note,
            options=items,
        )
