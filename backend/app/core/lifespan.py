"""FastAPI lifespan context manager.

Manages startup and shutdown hooks for the application.

Phase 3 responsibilities
------------------------
Startup:
    1. Initialise structured logging.
    2. Verify async PostgreSQL connection.
    3. Verify async Redis connection.
    4. Log a safe startup summary.

Shutdown:
    1. Close Redis connection pool.
    2. Dispose of the async engine connection pool.
    3. Log a clean shutdown message.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.exceptions import InfrastructureError
from app.infrastructure.database.engine import (
    dispose_engine,
    verify_database_connection,
)
from app.infrastructure.logging.config import configure_logging
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.redis.client import (
    close_redis_client,
    verify_redis_connection,
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Async context manager consumed by FastAPI as the application lifespan."""
    # ------------------------------------------------------------------ #
    # STARTUP                                                              #
    # ------------------------------------------------------------------ #
    from config.settings import get_settings  # noqa: PLC0415

    settings = get_settings()

    configure_logging(
        log_level=settings.effective_log_level,
        is_development=settings.is_development,
    )

    logger.info(
        "TradeAI API starting",
        extra={
            "environment": settings.APP_ENV.value,
            "log_level": settings.effective_log_level,
            "host": settings.HOST,
            "port": settings.PORT,
            "debug": settings.APP_DEBUG,
        },
    )

    # Verify database connectivity.
    try:
        await verify_database_connection()
    except (InfrastructureError, Exception) as exc:
        if settings.is_production:
            logger.error("Database connection failed during production startup.")
            raise
        logger.warning(f"Database connection check warning: {exc}")

    # Verify Redis connectivity.
    try:
        await verify_redis_connection()
    except (InfrastructureError, Exception) as exc:
        if settings.is_production:
            logger.error("Redis connection failed during production startup.")
            raise
        logger.warning(f"Redis connection check warning: {exc}")

    yield

    # ------------------------------------------------------------------ #
    # SHUTDOWN                                                             #
    # ------------------------------------------------------------------ #
    await close_redis_client()
    await dispose_engine()
    logger.info(
        "TradeAI API shutting down",
        extra={"environment": settings.APP_ENV.value},
    )
