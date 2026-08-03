"""Generic BaseRepository supporting CRUD, pagination, and soft delete."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel as PydanticBaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.base_model import BaseModel


class BaseRepository[T: BaseModel]:
    """Generic repository providing CRUD, pagination, and soft delete.

    Parameters
    ----------
    session:
        AsyncSession for database operations.
    model_cls:
        The ORM model class corresponding to T.
    """

    def __init__(self, session: AsyncSession, model_cls: type[T]) -> None:
        self.session = session
        self.model_cls = model_cls

    def _apply_soft_delete_filter(
        self, query: Any, *, include_deleted: bool = False
    ) -> Any:
        """Apply soft delete filter unless include_deleted is True."""
        if not include_deleted and hasattr(self.model_cls, "deleted_at"):
            query = query.where(self.model_cls.deleted_at.is_(None))
        return query

    async def create(self, obj_in: dict[str, Any] | PydanticBaseModel | T) -> T:
        """Create and persist a new entity.

        Parameters
        ----------
        obj_in:
            Dictionary, Pydantic schema, or ORM instance to create.

        Returns
        -------
        T
            The created entity.
        """
        if isinstance(obj_in, self.model_cls):
            db_obj = obj_in
        elif isinstance(obj_in, PydanticBaseModel):
            values = obj_in.model_dump(exclude_unset=True)
            db_obj = self.model_cls(**values)
        elif isinstance(obj_in, dict):
            db_obj = self.model_cls(**obj_in)
        else:
            raise TypeError(f"Invalid input type for creation: {type(obj_in)}")

        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def get(self, id: UUID | str, *, include_deleted: bool = False) -> T | None:
        """Get an entity by its primary key ID. Alias for get_by_id."""
        return await self.get_by_id(id, include_deleted=include_deleted)

    async def get_by_id(
        self, id: UUID | str, *, include_deleted: bool = False
    ) -> T | None:
        """Get an entity by its UUID primary key.

        Parameters
        ----------
        id:
            UUID primary key string or UUID object.
        include_deleted:
            Whether to include soft-deleted records.

        Returns
        -------
        T | None
            The entity if found, None otherwise.
        """
        target_id = UUID(str(id)) if isinstance(id, str) else id
        stmt = select(self.model_cls).where(self.model_cls.id == target_id)
        stmt = self._apply_soft_delete_filter(stmt, include_deleted=include_deleted)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> list[T]:
        """Fetch multiple entities with optional offset, limit, and soft-delete."""
        stmt = select(self.model_cls).offset(offset).limit(limit)
        stmt = self._apply_soft_delete_filter(stmt, include_deleted=include_deleted)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def paginate(
        self,
        *,
        page: int = 1,
        page_size: int = 20,
        include_deleted: bool = False,
    ) -> tuple[list[T], int, int]:
        """Paginate entities returning (items, total_count, total_pages)."""
        page = max(1, page)
        page_size = max(1, page_size)
        offset = (page - 1) * page_size

        total_count = await self.count(include_deleted=include_deleted)
        total_pages = math.ceil(total_count / page_size) if total_count > 0 else 0

        items = await self.get_multi(
            offset=offset, limit=page_size, include_deleted=include_deleted
        )
        return items, total_count, total_pages

    async def update(self, entity: T) -> T:
        """Persist mutations to an already-fetched ORM entity.

        The caller is responsible for fetching the entity via ``get_by_id``,
        applying field changes, and then calling this method to flush and
        refresh the instance.

        Parameters
        ----------
        entity:
            A mutated ORM instance that is already tracked by this session.

        Returns
        -------
        T
            The refreshed entity after flush.

        Example
        -------
        ::

            user = await repo.get_by_id(user_id)
            user.full_name = "Jane Doe"
            user.updated_at = datetime.now(UTC)
            user = await repo.update(user)
        """
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def soft_delete(self, id: UUID | str) -> bool:
        """Soft-delete an entity by setting deleted_at to current UTC time.

        Parameters
        ----------
        id:
            Entity primary key ID.

        Returns
        -------
        bool
            True if entity was soft-deleted, False if entity was not found.
        """
        target_id = UUID(str(id)) if isinstance(id, str) else id
        stmt = (
            update(self.model_cls)
            .where(self.model_cls.id == target_id)
            .where(self.model_cls.deleted_at.is_(None))
            .values(deleted_at=datetime.now(UTC))
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0  # type: ignore[attr-defined,no-any-return]

    async def exists(self, id: UUID | str, *, include_deleted: bool = False) -> bool:
        """Check if an entity exists by ID."""
        target_id = UUID(str(id)) if isinstance(id, str) else id
        stmt = (
            select(func.count())
            .select_from(self.model_cls)
            .where(self.model_cls.id == target_id)
        )
        stmt = self._apply_soft_delete_filter(stmt, include_deleted=include_deleted)
        result = await self.session.execute(stmt)
        count_val = result.scalar() or 0
        return count_val > 0

    async def count(self, *, include_deleted: bool = False) -> int:
        """Count total matching entities."""
        stmt = select(func.count()).select_from(self.model_cls)
        stmt = self._apply_soft_delete_filter(stmt, include_deleted=include_deleted)
        result = await self.session.execute(stmt)
        return result.scalar() or 0
