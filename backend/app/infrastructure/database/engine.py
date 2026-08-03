"""Async SQLAlchemy engine initialization and lifecycle management."""

from __future__ import annotations

import logging
from typing import Any

from config.settings import get_settings
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.exceptions import InfrastructureError

logger = logging.getLogger(__name__)

_engine: AsyncEngine | None = None


def get_engine(url: str | None = None) -> AsyncEngine:
    """Get or create the singleton AsyncEngine instance.

    Parameters
    ----------
    url:
        Optional database URL override. If None, uses ``settings.DATABASE_URL``.

    Returns
    -------
    AsyncEngine
        Configured SQLAlchemy async engine instance.
    """
    global _engine
    if _engine is None or url is not None:
        db_url = url or get_settings().DATABASE_URL
        engine_args: dict[str, Any] = {
            "echo": get_settings().APP_DEBUG,
            "future": True,
            "pool_pre_ping": True,
        }
        # Configure connection pool settings for PostgreSQL
        if "postgresql" in db_url:
            engine_args.update(
                {
                    "pool_size": 10,
                    "max_overflow": 20,
                    "pool_timeout": 30.0,
                    "pool_recycle": 1800,
                }
            )
        new_engine = create_async_engine(db_url, **engine_args)
        if url is None:
            _engine = new_engine
            return _engine
        return new_engine
    return _engine


async def dispose_engine() -> None:
    """Close all connections and dispose of the global engine."""
    global _engine
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Database engine connections disposed.")


async def verify_database_connection(url: str | None = None) -> bool:
    """Verify that an async connection can be established to PostgreSQL.

    Executes a simple ``SELECT 1`` check query.  Logs the result and raises
    ``InfrastructureError`` if the connection fails.

    Parameters
    ----------
    url:
        Optional database URL override.

    Returns
    -------
    bool
        True if the connection succeeded.

    Raises
    ------
    InfrastructureError
        If database connection fails.
    """
    db_url = url or get_settings().DATABASE_URL
    # Mask credentials in logs
    masked_url = db_url.split("@")[-1] if "@" in db_url else db_url

    logger.info("Verifying async database connection to %s...", masked_url)
    engine = get_engine(url=url)
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            val = result.scalar()
            if val == 1:
                logger.info("Database connection verification successful.")
                return True
            raise InfrastructureError("Database ping returned unexpected value.")
    except Exception as exc:
        msg = f"Failed to establish database connection to {masked_url}: {exc}"
        logger.error(msg)
        raise InfrastructureError(msg) from exc
