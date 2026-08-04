"""Unit tests for MarketDataService."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from app.services.market_data.service import MarketDataService
from app.services.market_data.types import RawOHLCV, RawQuote
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_quote_cache_miss_queries_provider_without_db_write() -> None:
    """Verify quote cache miss queries provider without DB write."""
    now = datetime.now(UTC)
    raw_quote = RawQuote(
        symbol="AAPL",
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

    mock_provider = AsyncMock()
    mock_provider.get_quote.return_value = raw_quote
    mock_session = AsyncMock(spec=AsyncSession)

    with (
        patch(
            "app.services.market_data.service.get_market_data_cache",
            return_value=None,
        ),
        patch(
            "app.services.market_data.service.set_market_data_cache"
        ) as mock_set_cache,
    ):
        service = MarketDataService(session=mock_session, provider=mock_provider)
        quote = await service.get_quote("AAPL")

        assert quote.symbol == "AAPL"
        assert quote.price == Decimal("180.50")
        mock_provider.get_quote.assert_called_once_with("AAPL")
        mock_set_cache.assert_called_once()
        # Ensure session was not called for DB persistence on quote
        mock_session.flush.assert_not_called()


@pytest.mark.asyncio
async def test_get_history_validates_and_persists_to_db() -> None:
    """Verify history fetch validates bars, persists Stock & MarketData, and caches."""
    now = datetime.now(UTC)
    raw_bar = RawOHLCV(
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

    mock_provider = AsyncMock()
    mock_provider.get_history.return_value = [raw_bar]
    mock_session = AsyncMock(spec=AsyncSession)

    with (
        patch(
            "app.services.market_data.service.get_market_data_cache",
            return_value=None,
        ),
        patch("app.services.market_data.service.set_market_data_cache"),
        patch(
            "app.services.market_data.service.StockRepository.get_or_create"
        ) as mock_get_or_create,
        patch(
            "app.services.market_data.service.MarketDataRepository.bulk_upsert"
        ) as mock_bulk_upsert,
    ):
        mock_stock = AsyncMock()
        mock_stock.id = "00000000-0000-0000-0000-000000000000"
        mock_get_or_create.return_value = mock_stock

        service = MarketDataService(session=mock_session, provider=mock_provider)
        history = await service.get_history("AAPL", period="1mo", interval="1d")

        assert history.symbol == "AAPL"
        assert history.count == 1
        mock_provider.get_history.assert_called_once_with("AAPL", "1mo", "1d")
        mock_get_or_create.assert_called_once()
        mock_bulk_upsert.assert_called_once()
