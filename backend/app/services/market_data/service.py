"""MarketDataService orchestrating provider calls, caching, validation, and
database persistence.
"""

from __future__ import annotations

from config.settings import get_settings
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.schemas.market_data import (
    HistoryResponse,
    IndicesResponse,
    OptionsResponse,
    QuoteResponse,
)
from app.infrastructure.database.models.market_data import MarketData
from app.infrastructure.database.repositories.market_data_repository import (
    MarketDataRepository,
)
from app.infrastructure.database.repositories.stock_repository import StockRepository
from app.infrastructure.redis.market_data_cache import (
    get_market_data_cache,
    set_market_data_cache,
)
from app.services.market_data.normalizer import MarketDataNormalizer
from app.services.market_data.providers.base import BaseMarketDataProvider
from app.services.market_data.providers.yahoo import YahooFinanceProvider
from app.services.market_data.types import ProviderHealth
from app.services.market_data.validator import MarketDataValidator


class MarketDataService:
    """Orchestrator for market data fetching, caching, normalization, validation,
    and persistence.

    Quote requests are cache-only (transient, no DB persistence).
    History requests and Celery ingestion tasks validate and persist OHLCV
    candles to PostgreSQL.
    """

    def __init__(
        self,
        session: AsyncSession,
        provider: BaseMarketDataProvider | None = None,
    ) -> None:
        self.session = session
        self.stock_repo = StockRepository(session)
        self.market_data_repo = MarketDataRepository(session)
        self.provider = provider or YahooFinanceProvider()

    async def get_provider_health(self) -> ProviderHealth:
        """Check provider health and return status."""
        return await self.provider.health_check()

    async def get_quote(self, symbol: str) -> QuoteResponse:
        """Retrieve real-time quote for a symbol.

        Quotes are cached in Redis but NOT stored in the database.
        """
        symbol_clean = symbol.strip().upper()
        settings = get_settings()
        cache_key = f"market_data:quote:{symbol_clean}"

        # 1. Check Redis cache
        cached_str = await get_market_data_cache(cache_key)
        if cached_str:
            return QuoteResponse.model_validate_json(cached_str)

        # 2. Cache miss — query provider
        raw_quote = await self.provider.get_quote(symbol_clean)

        # 3. Normalize
        normalized_quote = MarketDataNormalizer.normalize_quote(raw_quote)

        # 4. Cache in Redis (30s default)
        await set_market_data_cache(
            cache_key,
            normalized_quote.model_dump_json(),
            settings.MARKET_DATA_QUOTE_TTL_SECONDS,
        )

        return normalized_quote

    async def get_history(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> HistoryResponse:
        """Retrieve historical OHLCV candles, validate, persist to PostgreSQL,
        and cache.
        """
        symbol_clean = symbol.strip().upper()
        settings = get_settings()
        cache_key = f"market_data:history:{symbol_clean}:{period}:{interval}"

        # 1. Check Redis cache
        cached_str = await get_market_data_cache(cache_key)
        if cached_str:
            return HistoryResponse.model_validate_json(cached_str)

        # 2. Query provider
        raw_bars = await self.provider.get_history(symbol_clean, period, interval)

        if not raw_bars:
            empty_resp = HistoryResponse(
                symbol=symbol_clean,
                interval=interval,
                period=period,
                count=0,
                bars=[],
            )
            return empty_resp

        # 3. Validate batch
        validated_bars = MarketDataValidator.validate_batch(raw_bars)

        # 4. Normalize
        history_resp = MarketDataNormalizer.normalize_history(
            symbol_clean, period, interval, validated_bars
        )

        # 5. Persist to PostgreSQL (get or create stock, bulk upsert candles)
        stock = await self.stock_repo.get_or_create(
            symbol=symbol_clean,
            exchange=validated_bars[0].symbol if validated_bars else None,
        )

        db_records = [
            MarketData(
                stock_id=stock.id,
                timestamp=b.timestamp,
                interval=b.interval,
                open=b.open,
                high=b.high,
                low=b.low,
                close=b.close,
                volume=b.volume,
                provider=b.provider,
                provider_symbol=b.provider_symbol,
            )
            for b in validated_bars
        ]
        await self.market_data_repo.bulk_upsert(db_records)

        # 6. Cache in Redis (300s default)
        await set_market_data_cache(
            cache_key,
            history_resp.model_dump_json(),
            settings.MARKET_DATA_HISTORY_TTL_SECONDS,
        )

        return history_resp

    async def get_indices(self) -> IndicesResponse:
        """Retrieve market indices status and cache."""
        settings = get_settings()
        cache_key = "market_data:indices"

        # 1. Check Redis cache
        cached_str = await get_market_data_cache(cache_key)
        if cached_str:
            return IndicesResponse.model_validate_json(cached_str)

        # 2. Query provider
        raw_indices = await self.provider.get_indices()

        # 3. Normalize
        indices_resp = MarketDataNormalizer.normalize_indices(raw_indices)

        # 4. Cache in Redis (60s default)
        await set_market_data_cache(
            cache_key,
            indices_resp.model_dump_json(),
            settings.MARKET_DATA_INDICES_TTL_SECONDS,
        )

        return indices_resp

    async def get_options_chain(self, symbol: str) -> OptionsResponse:
        """Retrieve options chain contracts for symbol and cache."""
        symbol_clean = symbol.strip().upper()
        settings = get_settings()
        cache_key = f"market_data:options:{symbol_clean}"

        # 1. Check Redis cache
        cached_str = await get_market_data_cache(cache_key)
        if cached_str:
            return OptionsResponse.model_validate_json(cached_str)

        # 2. Query provider
        raw_options, provider_note = await self.provider.get_options_chain(symbol_clean)

        # 3. Normalize
        options_resp = MarketDataNormalizer.normalize_options(
            symbol_clean, raw_options, provider_note
        )

        # 4. Cache in Redis (30s default)
        await set_market_data_cache(
            cache_key,
            options_resp.model_dump_json(),
            settings.MARKET_DATA_OPTIONS_TTL_SECONDS,
        )

        return options_resp
