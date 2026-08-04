"""Celery background task for scheduled OHLCV market data ingestion."""

from __future__ import annotations

import asyncio
from typing import Any

from config.settings import get_settings

from app.infrastructure.database.session import get_session_factory
from app.infrastructure.logging.logger import get_logger
from app.services.market_data.providers.base import BaseMarketDataProvider
from app.services.market_data.service import MarketDataService
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)


async def run_market_data_ingestion(
    provider: BaseMarketDataProvider | None = None,
    watchlist: list[str] | None = None,
) -> dict[str, Any]:
    """Async engine function for market data ingestion task.

    Can be called directly by unit/integration tests without running Celery worker.
    """
    settings = get_settings()
    target_watchlist = watchlist or settings.MARKET_DATA_WATCHLIST

    logger.info(
        "Starting scheduled market data ingestion for %d symbols.",
        len(target_watchlist),
    )

    results: dict[str, Any] = {
        "symbols_processed": 0,
        "total_bars_saved": 0,
        "failed_symbols": [],
    }

    session_factory = get_session_factory()
    async with session_factory() as session:
        service = MarketDataService(session, provider=provider)

        for symbol in target_watchlist:
            try:
                history_resp = await service.get_history(
                    symbol, period="5d", interval="1d"
                )
                results["symbols_processed"] += 1
                results["total_bars_saved"] += history_resp.count
            except Exception as exc:
                logger.error(
                    "Failed to ingest market data for symbol %s: %s", symbol, exc
                )
                results["failed_symbols"].append(symbol)

        await session.commit()

    logger.info(
        "Completed market data ingestion. Processed: %d, Bars: %d, Failures: %d.",
        results["symbols_processed"],
        results["total_bars_saved"],
        len(results["failed_symbols"]),
    )

    return results


@celery_app.task(name="app.tasks.market_data_ingestion.ingest_latest_market_data")  # type: ignore[untyped-decorator]
def ingest_latest_market_data() -> dict[str, Any]:
    """Celery task entrypoint executing the async ingestion pipeline."""
    return asyncio.run(run_market_data_ingestion())
