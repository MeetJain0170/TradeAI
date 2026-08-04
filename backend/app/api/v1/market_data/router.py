"""Market Data API v1 endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.dependencies import CurrentActiveUserDep, MarketDataServiceDep
from app.api.envelope import SuccessResponse, success_response
from app.domain.schemas.market_data import (
    HistoryResponse,
    IndicesResponse,
    OptionsResponse,
    QuoteResponse,
)

router = APIRouter(prefix="/market-data", tags=["Market Data"])


@router.get("/indices", response_model=SuccessResponse[IndicesResponse])
async def get_indices(
    _user: CurrentActiveUserDep,
    market_data_service: MarketDataServiceDep,
) -> SuccessResponse[IndicesResponse]:
    """Retrieve status for major market indices.

    (S&P 500, Dow Jones, NASDAQ, NIFTY 50, SENSEX).
    """
    indices_resp = await market_data_service.get_indices()
    return success_response(indices_resp)


@router.get("/history/{symbol}", response_model=SuccessResponse[HistoryResponse])
async def get_history(
    symbol: str,
    _user: CurrentActiveUserDep,
    market_data_service: MarketDataServiceDep,
    period: str = Query(
        default="1mo",
        description="Historical period: 1d, 5d, 1mo, 3mo, 6mo, 1y, 5y, max.",
    ),
    interval: str = Query(
        default="1d", description="Candle interval: 1m, 5m, 15m, 1h, 1d, 1wk."
    ),
) -> SuccessResponse[HistoryResponse]:
    """Retrieve historical OHLCV candles for a symbol, persisted to database."""
    history_resp = await market_data_service.get_history(
        symbol, period=period, interval=interval
    )
    return success_response(history_resp)


@router.get("/options/{symbol}", response_model=SuccessResponse[OptionsResponse])
async def get_options_chain(
    symbol: str,
    _user: CurrentActiveUserDep,
    market_data_service: MarketDataServiceDep,
) -> SuccessResponse[OptionsResponse]:
    """Retrieve options chain contracts for a symbol."""
    options_resp = await market_data_service.get_options_chain(symbol)
    return success_response(options_resp)


@router.get("/{symbol}", response_model=SuccessResponse[QuoteResponse])
async def get_quote(
    symbol: str,
    _user: CurrentActiveUserDep,
    market_data_service: MarketDataServiceDep,
) -> SuccessResponse[QuoteResponse]:
    """Retrieve current real-time market quote for a symbol."""
    quote_resp = await market_data_service.get_quote(symbol)
    return success_response(quote_resp)
