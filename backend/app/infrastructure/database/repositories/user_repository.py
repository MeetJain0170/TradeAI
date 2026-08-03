"""UserRepository extending BaseRepository for User entities."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models.user import User
from app.infrastructure.database.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository[User]):
    """Repository handling User persistence and custom domain queries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_email(
        self,
        email: str,
        *,
        include_deleted: bool = False,
    ) -> User | None:
        """Fetch a user by email address.

        Parameters
        ----------
        email:
            User email address.
        include_deleted:
            Whether to include soft-deleted records.

        Returns
        -------
        User | None
            Matching User instance or None.
        """
        normalized_email = email.strip().lower()
        stmt = select(User).where(func.lower(User.email) == normalized_email)
        stmt = self._apply_soft_delete_filter(stmt, include_deleted=include_deleted)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def email_exists(
        self,
        email: str,
        *,
        include_deleted: bool = False,
    ) -> bool:
        """Check whether an email is already registered.

        Parameters
        ----------
        email:
            User email address.
        include_deleted:
            Whether to include soft-deleted records.

        Returns
        -------
        bool
            True if email exists in database.
        """
        normalized_email = email.strip().lower()
        stmt = (
            select(func.count())
            .select_from(User)
            .where(func.lower(User.email) == normalized_email)
        )
        stmt = self._apply_soft_delete_filter(stmt, include_deleted=include_deleted)
        result = await self.session.execute(stmt)
        count_val = result.scalar() or 0
        return count_val > 0
