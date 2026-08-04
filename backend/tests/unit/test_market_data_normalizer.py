"""Unit tests for MarketDataNormalizer."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

from app.services.market_data.normalizer import MarketDataNormalizer
from app.services.market_data.types import (
    RawIndex,
    RawOHLCV,
    RawOption,
    RawQuote,
)


def test_normalize_quote() -> None:
    """Verify RawQuote normalization maps fields correctly."""
    now = datetime.now(UTC)
    raw = RawQuote(
        symbol="aapl",
        price=Decimal("180.50"),
        open=Decimal("179.00"),
        high=Decimal("181.00"),
        low=Decimal("178.50"),
        prev_close=Decimal("179.50"),
        volume=50000000,
        currency="USD",
        exchange="NASDAQ",
        name="Apple Inc.",
        provider="yahoo",
        provider_symbol="AAPL",
        fetched_at=now,
    )
    quote = MarketDataNormalizer.normalize_quote(raw)

    assert quote.symbol == "AAPL"
    assert quote.price == Decimal("180.50")
    assert quote.volume == 50000000
    assert quote.provider == "yahoo"
    assert quote.provider_symbol == "AAPL"


def test_normalize_bar_and_history() -> None:
    """Verify RawOHLCV bar and history normalization."""
    now = datetime.now(UTC)
    raw_bar = RawOHLCV(
        symbol="msft",
        timestamp=now,
        interval="1d",
        open=Decimal("400.00"),
        high=Decimal("405.00"),
        low=Decimal("398.00"),
        close=Decimal("403.00"),
        volume=20000000,
        provider="yahoo",
        provider_symbol="MSFT",
    )

    bar = MarketDataNormalizer.normalize_bar(raw_bar)
    assert bar.open == Decimal("400.00")
    assert bar.close == Decimal("403.00")

    history = MarketDataNormalizer.normalize_history("msft", "1mo", "1d", [raw_bar])
    assert history.symbol == "MSFT"
    assert history.count == 1
    assert history.bars[0].close == Decimal("403.00")


def test_normalize_indices() -> None:
    """Verify RawIndex list normalization."""
    raw_index = RawIndex(
        symbol="^GSPC",
        name="S&P 500",
        price=Decimal("5000.00"),
        change=Decimal("25.00"),
        change_pct=Decimal("0.50"),
        provider="yahoo",
        provider_symbol="^GSPC",
    )
    indices = MarketDataNormalizer.normalize_indices([raw_index])
    assert len(indices.indices) == 1
    assert indices.indices[0].name == "S&P 500"
    assert indices.indices[0].price == Decimal("5000.00")


def test_normalize_options() -> None:
    """Verify RawOption list normalization."""
    raw_opt = RawOption(
        symbol="AAPL240315C00180000",
        expiry=date(2024, 3, 15),
        strike=Decimal("180.00"),
        option_type="call",
        last_price=Decimal("5.20"),
        volume=1200,
        open_interest=5000,
        provider="yahoo",
        provider_symbol="AAPL240315C00180000",
    )
    opts = MarketDataNormalizer.normalize_options("AAPL", [raw_opt], provider_note=None)
    assert opts.symbol == "AAPL"
    assert opts.count == 1
    assert opts.options[0].strike == Decimal("180.00")
    assert opts.options[0].option_type == "call"
