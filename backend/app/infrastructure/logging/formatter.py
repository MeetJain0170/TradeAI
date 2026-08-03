"""Structured JSON log formatter.

Converts every ``logging.LogRecord`` into a single-line JSON object so
that log-aggregation systems (Loki, CloudWatch, Datadog, …) can parse
and index fields without brittle regex patterns.

Fields emitted
--------------
``timestamp``
    ISO-8601 UTC timestamp (e.g. ``"2024-01-15T09:30:00.123456Z"``).
``level``
    Log level name: ``DEBUG``, ``INFO``, ``WARNING``, ``ERROR``, ``CRITICAL``.
``logger``
    Logger name (``record.name``), mirrors the module hierarchy.
``message``
    The formatted log message (after %-interpolation).
``service``
    Always ``"tradeai-api"`` — useful for log aggregation when multiple
    services emit to the same sink.
``environment``
    Current ``APP_ENV`` value (``development`` / ``staging`` /
    ``production``).  Populated lazily to avoid an import cycle at
    module-load time.
``request_id``
    Current request ID from the ``ContextVar`` in
    ``app.core.request_context``, or ``"unknown"`` when called outside
    a request context.
``module``
    Module where the log call was made.
``function``
    Function name where the log call was made.
``line``
    Line number where the log call was made.
``exception``
    Formatted traceback string, included only when the log record
    carries exception information.

On secrets in logs
------------------
The primary defence against leaking secrets is: **never pass sensitive
objects to a logger**.  Specifically:

* Do not log ``settings`` objects or any field containing a
  ``SecretStr``.
* Do not log ``request.headers`` — extract only the fields you need.
* Do not log ``Authorization`` header values.

As a secondary, defence-in-depth measure the formatter applies a
conservative pattern-based scrub to catch accidental leaks.  This
scrubber is intentionally narrow to avoid false positives on legitimate
field names such as ``market_api_key_count`` or ``api_key_rotation``.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

from app.core.request_context import get_request_id

# ------------------------------------------------------------------ #
# Secret scrubber                                                     #
# ------------------------------------------------------------------ #

# Narrow pattern: matches when a secret-bearing key appears as a standalone
# word (preceded by a non-word character or start of string), followed by
# an assignment/colon separator, then *everything* to the end of the line
# or a structural delimiter.  Capturing to end-of-line ensures multi-word
# values (e.g. "token=Bearer eyJhb...") are fully redacted.
_SECRET_PATTERN: re.Pattern[str] = re.compile(
    r"(?i)(?<![\w_])(password|secret_key|secret|api_key|token|auth_key|private_key)"
    r"([:=\s]+)([^\n,&}{;]+)",
)
_REDACTED: str = "***REDACTED***"


def _scrub_secrets(message: str) -> str:
    """Replace secret-looking ``key=value`` pairs with a redaction marker.

    This is a defence-in-depth measure, not the primary secret-protection
    strategy.  Do not rely on this function as the sole mechanism for
    preventing secret leakage.

    Parameters
    ----------
    message:
        Raw log message string.

    Returns
    -------
    str
        The message with sensitive values replaced by ``***REDACTED***``.
    """
    return _SECRET_PATTERN.sub(r"\1\2" + _REDACTED, message)


# ------------------------------------------------------------------ #
# Formatter                                                           #
# ------------------------------------------------------------------ #


class JSONFormatter(logging.Formatter):
    """Emit log records as single-line JSON objects.

    Parameters
    ----------
    service:
        Logical service name appended to every log line.
        Defaults to ``"tradeai-api"``.
    environment:
        Deployment environment string (``development`` / ``staging`` /
        ``production``).  When *None*, the formatter reads
        ``APP_ENV`` from settings on first use (lazy import to avoid
        circular dependencies at module load time).
    """

    def __init__(
        self,
        service: str = "tradeai-api",
        environment: str | None = None,
    ) -> None:
        super().__init__()
        self._service = service
        self._environment = environment

    def _get_environment(self) -> str:
        """Return the environment string, resolving lazily from settings."""
        if self._environment is None:
            try:
                from config.settings import get_settings  # noqa: PLC0415

                self._environment = get_settings().APP_ENV.value
            except Exception:  # noqa: BLE001
                self._environment = "unknown"
        return self._environment

    def format(self, record: logging.LogRecord) -> str:
        """Format *record* as a JSON string.

        Parameters
        ----------
        record:
            The log record to format.

        Returns
        -------
        str
            A single-line JSON string (no trailing newline).
        """
        message: str = record.getMessage()
        message = _scrub_secrets(message)

        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "service": self._service,
            "environment": self._get_environment(),
            "logger": record.name,
            "message": message,
            "request_id": get_request_id(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(payload, default=str, ensure_ascii=False)
