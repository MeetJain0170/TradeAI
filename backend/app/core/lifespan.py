"""FastAPI lifespan context manager.

Manages startup and shutdown hooks for the application.

Phase 2 responsibilities
------------------------
Startup:
    1. Initialise structured logging.
    2. Verify async PostgreSQL connection (fail fast in production, warning in dev).
    3. Log a safe startup summary (no secrets or connection strings).

Shutdown:
    1. Dispose of the async engine connection pool.
    2. Log a clean shutdown message.
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

    # Verify database connectivity. Fail fast in production; log warning in dev.
    try:
        await verify_database_connection()
    except (InfrastructureError, Exception) as exc:
        if settings.is_production:
            logger.error(
                "Database connection failed during production startup. Aborting."
            )
            raise
        logger.warning(
            f"Database connection check failed during startup: {exc}. "
            "Continuing startup as environment is non-production."
        )

    yield

    # ------------------------------------------------------------------ #
    # SHUTDOWN                                                             #
    # ------------------------------------------------------------------ #
    await dispose_engine()
    logger.info(
        "TradeAI API shutting down",
        extra={"environment": settings.APP_ENV.value},
    )
