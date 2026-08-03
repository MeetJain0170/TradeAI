"""Logger factory for the TradeAI backend.

Every module in the application should obtain its logger through this
factory rather than calling ``logging.getLogger`` directly.  This
ensures all loggers are part of the same hierarchy and pick up the
JSON formatter configured in ``configure_logging()``.

Usage
-----
::

    from app.infrastructure.logging.logger import get_logger

    logger = get_logger(__name__)

    logger.info("Market data fetched", extra={"symbol": "RELIANCE"})

Never pass sensitive objects to the logger
------------------------------------------
The following must **never** be passed as a log message or ``extra``
value:

* ``settings`` instances or any ``SecretStr`` field
* ``request.headers`` in their entirety
* ``Authorization`` header values
* Passwords, API keys, or tokens in any form

Pass only the specific, non-sensitive fields you need (e.g., the HTTP
method and path, never the full header dict).
"""

from __future__ import annotations

import logging


def get_logger(name: str) -> logging.Logger:
    """Return a named logger that participates in the application's
    logging hierarchy.

    Parameters
    ----------
    name:
        Typically ``__name__`` of the calling module, e.g.
        ``"app.services.market_data.yahoo_finance_provider"``.

    Returns
    -------
    logging.Logger
        A standard Python logger.  Its effective level and handlers are
        inherited from the root logger configured by
        ``configure_logging()``.
    """
    return logging.getLogger(name)
