"""FastAPI dependency injection for database sessions and repositories.

Services and route handlers must never instantiate sessions or
repositories directly.  Instead, they declare them as function
parameters using FastAPI's ``Depends`` system::

    @router.get("/users/{user_id}")
    async def get_user(
        user_id: UUID,
        user_repo: UserRepositoryDep,
    ) -> UserResponse:
        ...
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.repositories.user_repository import UserRepository
from app.infrastructure.database.session import get_db_session


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Yield an AsyncSession for the current request.

    Commits on success, rolls back on exception, and always closes
    the session when the response is sent.
    """
    async for session in get_db_session():
        yield session


# --------------------------------------------------------------------- #
# Annotated type aliases — concise for route signatures                  #
# --------------------------------------------------------------------- #

DbSession = Annotated[AsyncSession, Depends(get_db)]
"""Inject an ``AsyncSession`` into a route handler or service."""


def get_user_repository(session: DbSession) -> UserRepository:
    """Provide a ``UserRepository`` bound to the current session."""
    return UserRepository(session)


UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
"""Inject a ``UserRepository`` into a route handler or service."""
