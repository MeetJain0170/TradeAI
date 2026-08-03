"""Logging configuration for the TradeAI backend.

Call ``configure_logging()`` once during application startup (from
``lifespan.py``) before any log message is emitted.  Calling it more
than once is safe — it replaces handlers idempotently.

Design decisions
----------------
* The root logger receives a single ``StreamHandler`` that writes JSON
  to ``stdout`` (picked up by Docker / log shippers automatically).
* ``uvicorn.access`` log verbosity is **environment-configurable**: in
  development all access logs are shown; in staging/production the
  level is raised to ``WARNING`` to reduce noise without hiding errors.
  This avoids the trap of silencing access logs globally, which makes
  local debugging painful.
* Third-party library loggers that emit excessive noise at DEBUG/INFO
  are suppressed to ``WARNING`` only — they are never fully silenced so
  that genuine warnings still surface.
"""

from __future__ import annotations

import logging
import sys

from app.infrastructure.logging.formatter import JSONFormatter


def configure_logging(
    log_level: str = "INFO",
    *,
    is_development: bool = True,
) -> None:
    """Configure structured JSON logging for the application.

    This function is idempotent: calling it multiple times (e.g., in
    tests) replaces the existing handler rather than adding duplicates.

    Parameters
    ----------
    log_level:
        Root log level string: ``DEBUG``, ``INFO``, ``WARNING``,
        ``ERROR``, or ``CRITICAL``.  Typically sourced from
        ``settings.effective_log_level``.
    is_development:
        When *True*, ``uvicorn.access`` retains its default level so
        HTTP access logs are visible during local development.
        When *False* (staging / production), ``uvicorn.access`` is
        raised to ``WARNING`` to reduce log volume.
    """
    numeric_level = logging.getLevelName(log_level.upper())
    if not isinstance(numeric_level, int):
        # Fall back to INFO rather than crashing if an invalid level slips through.
        numeric_level = logging.INFO

    formatter = JSONFormatter()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.setLevel(numeric_level)

    root_logger = logging.getLogger()
    # Remove any handlers added by uvicorn or previous configure_logging calls.
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(numeric_level)

    # ------------------------------------------------------------------ #
    # Third-party logger tuning                                           #
    # ------------------------------------------------------------------ #

    # uvicorn.access: show in development (level NOTSET → inherits root);
    # suppress (WARNING+) in staging/production to reduce log volume.
    uvicorn_access = logging.getLogger("uvicorn.access")
    if is_development:
        uvicorn_access.setLevel(logging.NOTSET)
    else:
        uvicorn_access.setLevel(logging.WARNING)

    # sqlalchemy.engine is extremely verbose at DEBUG (prints every SQL
    # statement).  Keep it at WARNING unless the root level is DEBUG,
    # in which case it inherits the root level automatically.
    if numeric_level > logging.DEBUG:
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    # httpx / httpcore can be very chatty at DEBUG during external calls.
    if numeric_level > logging.DEBUG:
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("httpcore").setLevel(logging.WARNING)
