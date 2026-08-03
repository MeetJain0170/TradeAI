"""FastAPI lifespan context manager.

Manages startup and shutdown hooks for the application.  FastAPI runs
the code before the ``yield`` on startup and the code after the
``yield`` on shutdown.

Current responsibilities (Phase 1)
-----------------------------------
Startup:
    1. Initialise structured logging (must happen before any log call).
    2. Log a safe startup summary (environment, log level, host, port —
       never secrets).

Shutdown:
    1. Log a clean shutdown message.

Future phases will extend this with:
    * Phase 2 — PostgreSQL async engine startup / disposal
    * Phase 3 — Redis connection pool startup / disposal
    * Phase 8 — Vector DB client startup / disposal

No resource that requires cleanup is initialised here yet; this file
exists so that later phases have a single, well-known place to add
lifecycle hooks without touching ``main.py``.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infrastructure.logging.config import configure_logging
from app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Async context manager consumed by FastAPI as the application lifespan.

    Parameters
    ----------
    app:
        The FastAPI application instance.  Passed by FastAPI automatically;
        available here if startup hooks need to attach state to
        ``app.state``.
    """
    # ------------------------------------------------------------------ #
    # STARTUP                                                              #
    # ------------------------------------------------------------------ #
    from config.settings import get_settings  # noqa: PLC0415

    settings = get_settings()

    configure_logging(
        log_level=settings.effective_log_level,
        is_development=settings.is_development,
    )

    # Log a safe summary — never include secrets, connection strings,
    # or any field whose value could contain credentials.
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

    yield

    # ------------------------------------------------------------------ #
    # SHUTDOWN                                                             #
    # ------------------------------------------------------------------ #
    logger.info(
        "TradeAI API shutting down",
        extra={"environment": settings.APP_ENV.value},
    )
