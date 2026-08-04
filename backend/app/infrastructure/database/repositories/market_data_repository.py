"""MarketDataRepository extending BaseRepository for MarketData entities."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from sqlalchemy import CursorResult, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.market_data import MarketData
from app.infrastructure.database.repositories.base_repository import BaseRepository


class MarketDataRepository(BaseRepository[MarketData]):
    """Repository handling MarketData OHLCV candle persistence and queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, MarketData)

    async def get_latest(
        self,
        stock_id: UUID,
        interval: str = "1d",
    ) -> MarketData | None:
        """Fetch the most recent candle for a given stock and interval."""
        stmt = (
            select(MarketData)
            .where(MarketData.stock_id == stock_id)
            .where(MarketData.interval == interval)
            .order_by(MarketData.timestamp.desc())
            .limit(1)
        )
        stmt = self._apply_soft_delete_filter(stmt)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_history(
        self,
        stock_id: UUID,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        interval: str = "1d",
        limit: int = 1000,
    ) -> list[MarketData]:
        """Fetch historical candles for a stock within an optional time range."""
        stmt = (
            select(MarketData)
            .where(MarketData.stock_id == stock_id)
            .where(MarketData.interval == interval)
        )

        if start is not None:
            stmt = stmt.where(MarketData.timestamp >= start)

        if end is not None:
            stmt = stmt.where(MarketData.timestamp <= end)

        stmt = stmt.order_by(MarketData.timestamp.asc()).limit(limit)
        stmt = self._apply_soft_delete_filter(stmt)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_upsert(
        self,
        records: Sequence[dict[str, object] | MarketData],
    ) -> int:
        """Bulk insert candles, skipping duplicates on (stock_id, timestamp, interval).

        Returns
        -------
        int
            Number of inserted rows.
        """
        if not records:
            return 0

        now = datetime.now(UTC)
        values_list: list[dict[str, object]] = []

        for r in records:
            if isinstance(r, MarketData):
                values_list.append(
                    {
                        "id": uuid4(),
                        "stock_id": r.stock_id,
                        "timestamp": r.timestamp,
                        "interval": r.interval,
                        "open": r.open,
                        "high": r.high,
                        "low": r.low,
                        "close": r.close,
                        "volume": r.volume,
                        "provider": r.provider,
                        "provider_symbol": r.provider_symbol,
                        "created_at": now,
                        "updated_at": now,
                        "deleted_at": None,
                    }
                )
            else:
                values_list.append(r)

        stmt = (
            pg_insert(MarketData)
            .values(values_list)
            .on_conflict_do_nothing(
                index_elements=["stock_id", "timestamp", "interval"]
            )
        )

        result = await self.session.execute(stmt)
        await self.session.flush()

        return cast(CursorResult[Any], result).rowcount
