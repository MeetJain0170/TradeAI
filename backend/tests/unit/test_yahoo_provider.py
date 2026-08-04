"""Unit tests for YahooFinanceProvider."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from app.core.exceptions import InfrastructureError
from app.services.market_data.providers.yahoo import YahooFinanceProvider


@pytest.mark.asyncio
async def test_yahoo_provider_get_quote() -> None:
    """Verify YahooFinanceProvider maps client quote dict to RawQuote."""
    mock_client = MagicMock()
    mock_client.fetch_quote.return_value = {
        "symbol": "AAPL",
        "provider_symbol": "AAPL",
        "price": 180.50,
        "open": 179.00,
        "high": 181.00,
        "low": 178.50,
        "prev_close": 179.50,
        "volume": 50000000,
        "currency": "USD",
        "exchange": "NASDAQ",
        "name": "Apple Inc.",
        "fetched_at": datetime.now(UTC),
    }

    provider = YahooFinanceProvider(client=mock_client)
    quote = await provider.get_quote("AAPL")

    assert quote.symbol == "AAPL"
    assert str(quote.price) == "180.5"
    assert quote.provider == "yahoo"
    assert quote.provider_symbol == "AAPL"


@pytest.mark.asyncio
async def test_yahoo_provider_health_check_success() -> None:
    """Verify health_check returns ProviderHealth on success."""
    mock_client = MagicMock()
    mock_client.fetch_quote.return_value = {
        "symbol": "AAPL",
        "price": 180.50,
        "open": 179.00,
        "high": 181.00,
        "low": 178.50,
        "prev_close": 179.50,
        "volume": 50000000,
        "currency": "USD",
        "exchange": "NASDAQ",
        "name": "Apple Inc.",
        "provider_symbol": "AAPL",
        "fetched_at": datetime.now(UTC),
    }

    provider = YahooFinanceProvider(client=mock_client)
    health = await provider.health_check()

    assert health.healthy is True
    assert health.provider == "yahoo"
    assert health.latency_ms >= 0
    assert health.error is None


@pytest.mark.asyncio
async def test_yahoo_provider_network_error_raises_infrastructure_error() -> None:
    """Verify client exception is wrapped in InfrastructureError."""
    mock_client = MagicMock()
    mock_client.fetch_quote.side_effect = RuntimeError("Network timeout")

    provider = YahooFinanceProvider(client=mock_client)
    with pytest.raises(InfrastructureError) as exc:
        await provider.get_quote("AAPL")
    assert "Network timeout" in str(exc.value)
