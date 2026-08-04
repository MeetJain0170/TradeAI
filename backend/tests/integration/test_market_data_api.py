"""Integration tests for Market Data API endpoints."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from app.api.dependencies import get_db
from app.domain.schemas.market_data import (
    HistoryResponse,
    IndicesResponse,
    OHLCVBar,
    OptionsResponse,
    QuoteResponse,
)
from app.main import app
from app.security.jwt import JWTService
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def async_client(
    db_session: AsyncSession,
) -> AsyncGenerator[AsyncClient]:
    """Provide an AsyncClient with the database session dependency overridden."""

    async def _override_get_db() -> AsyncGenerator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_headers(async_client: AsyncClient) -> dict[str, str]:
    """Register a user and return Authorization header dictionary."""
    reg_payload = {
        "email": "marketuser@example.com",
        "password": "StrongPassword123!",
        "password_confirm": "StrongPassword123!",
        "full_name": "Market User",
    }
    resp = await async_client.post("/api/v1/auth/register", json=reg_payload)
    user_id = resp.json()["data"]["id"]

    token, _ = JWTService.create_access_token(user_id, "marketuser@example.com", "USER")
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401(async_client: AsyncClient) -> None:
    """Verify endpoint without Bearer token returns 401."""
    resp = await async_client.get("/api/v1/market-data/AAPL")
    assert resp.status_code == 401
    assert resp.json()["success"] is False


@pytest.mark.asyncio
async def test_get_quote_endpoint(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Verify GET /api/v1/market-data/{symbol} returns quote envelope."""
    mock_quote = QuoteResponse(
        symbol="AAPL",
        price=180.50,  # type: ignore[arg-type]
        open=179.00,  # type: ignore[arg-type]
        high=181.00,  # type: ignore[arg-type]
        low=178.50,  # type: ignore[arg-type]
        prev_close=179.50,  # type: ignore[arg-type]
        volume=50000000,
        currency="USD",
        exchange="NASDAQ",
        name="Apple Inc.",
        provider="yahoo",
        provider_symbol="AAPL",
        fetched_at="2026-08-04T12:00:00Z",  # type: ignore[arg-type]
    )

    with patch(
        "app.services.market_data.service.MarketDataService.get_quote",
        new_callable=AsyncMock,
    ) as mock_get_quote:
        mock_get_quote.return_value = mock_quote
        resp = await async_client.get("/api/v1/market-data/AAPL", headers=auth_headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["symbol"] == "AAPL"
        assert float(data["data"]["price"]) == 180.50


@pytest.mark.asyncio
async def test_get_history_endpoint(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Verify GET /api/v1/market-data/history/{symbol} returns history envelope."""
    mock_history = HistoryResponse(
        symbol="AAPL",
        interval="1d",
        period="1mo",
        count=1,
        bars=[
            OHLCVBar(
                timestamp="2026-08-04T00:00:00Z",  # type: ignore[arg-type]
                open=180.0,  # type: ignore[arg-type]
                high=185.0,  # type: ignore[arg-type]
                low=179.0,  # type: ignore[arg-type]
                close=182.0,  # type: ignore[arg-type]
                volume=1000000,
                interval="1d",
                provider="yahoo",
                provider_symbol="AAPL",
            )
        ],
    )

    with patch(
        "app.services.market_data.service.MarketDataService.get_history",
        new_callable=AsyncMock,
    ) as mock_get_history:
        mock_get_history.return_value = mock_history
        resp = await async_client.get(
            "/api/v1/market-data/history/AAPL", headers=auth_headers
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["symbol"] == "AAPL"
        assert data["data"]["count"] == 1


@pytest.mark.asyncio
async def test_get_indices_endpoint(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Verify GET /api/v1/market-data/indices returns indices envelope."""
    mock_indices = IndicesResponse(indices=[])

    with patch(
        "app.services.market_data.service.MarketDataService.get_indices",
        new_callable=AsyncMock,
    ) as mock_get_indices:
        mock_get_indices.return_value = mock_indices
        resp = await async_client.get(
            "/api/v1/market-data/indices", headers=auth_headers
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "indices" in data["data"]


@pytest.mark.asyncio
async def test_get_options_endpoint(
    async_client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Verify GET /api/v1/market-data/options/{symbol} returns options envelope."""
    mock_options = OptionsResponse(
        symbol="AAPL",
        count=0,
        provider_note="No options chain data available.",
        options=[],
    )

    with patch(
        "app.services.market_data.service.MarketDataService.get_options_chain",
        new_callable=AsyncMock,
    ) as mock_get_options:
        mock_get_options.return_value = mock_options
        resp = await async_client.get(
            "/api/v1/market-data/options/AAPL", headers=auth_headers
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["data"]["symbol"] == "AAPL"
        assert data["data"]["provider_note"] == "No options chain data available."
