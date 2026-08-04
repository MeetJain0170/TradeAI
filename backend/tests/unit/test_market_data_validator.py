"""Unit tests for MarketDataValidator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from app.core.exceptions import ValidationError
from app.services.market_data.types import RawOHLCV
from app.services.market_data.validator import MarketDataValidator


def test_valid_bar_passes() -> None:
    """Verify clean OHLCV bar passes validation without error."""
    now = datetime.now(UTC)
    bar = RawOHLCV(
        symbol="AAPL",
        timestamp=now,
        interval="1d",
        open=Decimal("180.00"),
        high=Decimal("185.00"),
        low=Decimal("179.00"),
        close=Decimal("182.00"),
        volume=1000000,
        provider="yahoo",
        provider_symbol="AAPL",
    )
    MarketDataValidator.validate_bar(bar)


def test_high_less_than_low_rejected() -> None:
    """Verify high < low raises ValidationError."""
    now = datetime.now(UTC)
    bar = RawOHLCV(
        symbol="AAPL",
        timestamp=now,
        interval="1d",
        open=Decimal("180.00"),
        high=Decimal("170.00"),  # invalid
        low=Decimal("179.00"),
        close=Decimal("175.00"),
        volume=1000000,
        provider="yahoo",
        provider_symbol="AAPL",
    )
    with pytest.raises(ValidationError) as exc:
        MarketDataValidator.validate_bar(bar)
    assert "high_gte_low" in str(exc.value.details)


def test_open_outside_bounds_rejected() -> None:
    """Verify open outside [low, high] raises ValidationError."""
    now = datetime.now(UTC)
    bar = RawOHLCV(
        symbol="AAPL",
        timestamp=now,
        interval="1d",
        open=Decimal("190.00"),  # invalid (> high)
        high=Decimal("185.00"),
        low=Decimal("179.00"),
        close=Decimal("182.00"),
        volume=1000000,
        provider="yahoo",
        provider_symbol="AAPL",
    )
    with pytest.raises(ValidationError) as exc:
        MarketDataValidator.validate_bar(bar)
    assert "open_within_bounds" in str(exc.value.details)


def test_close_outside_bounds_rejected() -> None:
    """Verify close outside [low, high] raises ValidationError."""
    now = datetime.now(UTC)
    bar = RawOHLCV(
        symbol="AAPL",
        timestamp=now,
        interval="1d",
        open=Decimal("180.00"),
        high=Decimal("185.00"),
        low=Decimal("179.00"),
        close=Decimal("170.00"),  # invalid (< low)
        volume=1000000,
        provider="yahoo",
        provider_symbol="AAPL",
    )
    with pytest.raises(ValidationError) as exc:
        MarketDataValidator.validate_bar(bar)
    assert "close_within_bounds" in str(exc.value.details)


def test_negative_volume_rejected() -> None:
    """Verify volume < 0 raises ValidationError."""
    now = datetime.now(UTC)
    bar = RawOHLCV(
        symbol="AAPL",
        timestamp=now,
        interval="1d",
        open=Decimal("180.00"),
        high=Decimal("185.00"),
        low=Decimal("179.00"),
        close=Decimal("182.00"),
        volume=-100,  # invalid
        provider="yahoo",
        provider_symbol="AAPL",
    )
    with pytest.raises(ValidationError) as exc:
        MarketDataValidator.validate_bar(bar)
    assert "volume_non_negative" in str(exc.value.details)


def test_future_timestamp_rejected() -> None:
    """Verify timestamp > now + 60s raises ValidationError."""
    future_dt = datetime.now(UTC) + timedelta(minutes=10)
    bar = RawOHLCV(
        symbol="AAPL",
        timestamp=future_dt,
        interval="1d",
        open=Decimal("180.00"),
        high=Decimal("185.00"),
        low=Decimal("179.00"),
        close=Decimal("182.00"),
        volume=1000,
        provider="yahoo",
        provider_symbol="AAPL",
    )
    with pytest.raises(ValidationError) as exc:
        MarketDataValidator.validate_bar(bar)
    assert "no_future_timestamps" in str(exc.value.details)


def test_duplicate_batch_keys_rejected() -> None:
    """Verify duplicate timestamp/interval in batch raises ValidationError."""
    now = datetime.now(UTC)
    bar1 = RawOHLCV(
        symbol="AAPL",
        timestamp=now,
        interval="1d",
        open=Decimal("180.00"),
        high=Decimal("185.00"),
        low=Decimal("179.00"),
        close=Decimal("182.00"),
        volume=1000,
        provider="yahoo",
        provider_symbol="AAPL",
    )
    bar2 = RawOHLCV(
        symbol="AAPL",
        timestamp=now,  # duplicate
        interval="1d",
        open=Decimal("181.00"),
        high=Decimal("186.00"),
        low=Decimal("180.00"),
        close=Decimal("183.00"),
        volume=2000,
        provider="yahoo",
        provider_symbol="AAPL",
    )

    with pytest.raises(ValidationError) as exc:
        MarketDataValidator.validate_batch([bar1, bar2])
    assert "no_duplicate_batch_keys" in str(exc.value.details)
