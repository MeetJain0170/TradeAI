"""Validation layer for market data records to prevent garbage inputs from
persisting.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import InvalidOperation

from app.core.exceptions import ValidationError
from app.services.market_data.types import RawOHLCV


class MarketDataValidator:
    """Pure validator methods enforcing integrity of OHLCV market candles."""

    FUTURE_TOLERANCE_SECONDS = 60

    @classmethod
    def validate_bar(cls, bar: RawOHLCV) -> None:
        """Validate a single RawOHLCV bar.

        Raises
        ------
        ValidationError
            If any candle integrity rule is violated.
        """
        # 1. High < Low
        try:
            if bar.high < bar.low:
                raise ValidationError(
                    (
                        f"Invalid candle for {bar.symbol}: "
                        f"high price ({bar.high}) "
                        f"is less than low price ({bar.low})."
                    ),
                    details={
                        "symbol": bar.symbol,
                        "timestamp": bar.timestamp.isoformat(),
                        "high": str(bar.high),
                        "low": str(bar.low),
                        "rule": "high_gte_low",
                    },
                )
        except InvalidOperation:
            print("=" * 60)
            print("BAD BAR")
            print(bar)
            print("high :", repr(bar.high))
            print("low  :", repr(bar.low))
            print("open :", repr(bar.open))
            print("close:", repr(bar.close))
            print("=" * 60)
            raise

        # 2. Open outside [low, high]
        if not (bar.low <= bar.open <= bar.high):
            raise ValidationError(
                (
                    f"Invalid candle for {bar.symbol}: "
                    f"open price ({bar.open}) is outside "
                    f"[low={bar.low}, high={bar.high}]."
                ),
                details={
                    "symbol": bar.symbol,
                    "timestamp": bar.timestamp.isoformat(),
                    "open": str(bar.open),
                    "rule": "open_within_bounds",
                },
            )

        # 3. Close outside [low, high]
        if not (bar.low <= bar.close <= bar.high):
            raise ValidationError(
                (
                    f"Invalid candle for {bar.symbol}: "
                    f"close price ({bar.close}) is outside "
                    f"[low={bar.low}, high={bar.high}]."
                ),
                details={
                    "symbol": bar.symbol,
                    "timestamp": bar.timestamp.isoformat(),
                    "close": str(bar.close),
                    "rule": "close_within_bounds",
                },
            )

        # 4. Volume < 0
        if bar.volume < 0:
            raise ValidationError(
                (
                    f"Invalid candle for {bar.symbol}: "
                    f"volume ({bar.volume}) cannot be negative."
                ),
                details={
                    "symbol": bar.symbol,
                    "timestamp": bar.timestamp.isoformat(),
                    "volume": bar.volume,
                    "rule": "volume_non_negative",
                },
            )

        # 5. Future timestamp (> now + 60s tolerance)
        now_utc = datetime.now(UTC)
        max_allowed_dt = now_utc + timedelta(seconds=cls.FUTURE_TOLERANCE_SECONDS)
        bar_dt = (
            bar.timestamp.astimezone(UTC)
            if bar.timestamp.tzinfo
            else bar.timestamp.replace(tzinfo=UTC)
        )

        if bar_dt > max_allowed_dt:
            raise ValidationError(
                (
                    f"Invalid candle for {bar.symbol}: "
                    f"timestamp ({bar_dt.isoformat()}) is in the future."
                ),
                details={
                    "symbol": bar.symbol,
                    "timestamp": bar_dt.isoformat(),
                    "rule": "no_future_timestamps",
                },
            )

    @classmethod
    def validate_batch(cls, bars: list[RawOHLCV]) -> list[RawOHLCV]:
        """Validate a batch of bars and filter out invalid/duplicate entries.

        Returns
        -------
        list[RawOHLCV]
            The list of valid, deduplicated bars.

        Raises
        ------
        ValidationError
            If duplicate entries exist within the same batch.
        """
        seen_keys: set[tuple[str, datetime, str]] = set()
        validated: list[RawOHLCV] = []

        for b in bars:
            cls.validate_bar(b)

            b_dt = (
                b.timestamp.astimezone(UTC)
                if b.timestamp.tzinfo
                else b.timestamp.replace(tzinfo=UTC)
            )
            key = (b.symbol.upper(), b_dt, b.interval)

            if key in seen_keys:
                raise ValidationError(
                    (
                        f"Duplicate candle detected in batch for {b.symbol} "
                        f"at {b_dt.isoformat()} ({b.interval})."
                    ),
                    details={
                        "symbol": b.symbol,
                        "timestamp": b_dt.isoformat(),
                        "interval": b.interval,
                        "rule": "no_duplicate_batch_keys",
                    },
                )
            seen_keys.add(key)
            validated.append(b)

        return validated
