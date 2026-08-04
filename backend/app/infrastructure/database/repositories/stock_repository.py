"""StockRepository extending BaseRepository for Stock entities."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.stock import Stock
from app.infrastructure.database.repositories.base_repository import BaseRepository


class StockRepository(BaseRepository[Stock]):
    """Repository handling Stock entity persistence and queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Stock)

    async def get_by_symbol(
        self,
        symbol: str,
        *,
        include_deleted: bool = False,
    ) -> Stock | None:
        """Fetch a stock by canonical symbol (case-insensitive)."""
        normalized_symbol = symbol.strip().upper()
        stmt = select(Stock).where(Stock.symbol == normalized_symbol)
        stmt = self._apply_soft_delete_filter(stmt, include_deleted=include_deleted)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        symbol: str,
        **defaults: Any,
    ) -> Stock:
        """Fetch existing Stock by symbol or create a new row if absent."""
        normalized_symbol = symbol.strip().upper()
        existing = await self.get_by_symbol(normalized_symbol)
        if existing is not None:
            return existing

        new_stock = Stock(
            symbol=normalized_symbol,
            name=defaults.get("name"),
            exchange=defaults.get("exchange"),
            currency=defaults.get("currency"),
            sector=defaults.get("sector"),
            industry=defaults.get("industry"),
        )
        return await self.create(new_stock)
