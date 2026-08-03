"""Async session factory and FastAPI dependency context manager."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from app.infrastructure.database.engine import get_engine

_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_session_factory(
    engine: AsyncEngine | None = None,
) -> async_sessionmaker[AsyncSession]:
    """Get or create the async session factory singleton.

    Parameters
    ----------
    engine:
        Optional engine override.

    Returns
    -------
    async_sessionmaker[AsyncSession]
        Async session factory bound to the engine.
    """
    global _session_factory
    if _session_factory is None or engine is not None:
        target_engine = engine or get_engine()
        factory = async_sessionmaker(
            bind=target_engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
        if engine is None:
            _session_factory = factory
            return _session_factory
        return factory
    return _session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """FastAPI dependency yielding an AsyncSession with automatic transaction handling.

    Rolls back transaction on error and closes the session on exit.
    """
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
