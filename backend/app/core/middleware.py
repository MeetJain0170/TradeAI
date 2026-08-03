"""ASGI middleware for the TradeAI backend.

Two middleware classes are provided:

``RequestIDMiddleware``
    Ensures every request has a unique identifier.  It reads the
    ``X-Request-ID`` header if present (allowing upstream load
    balancers or clients to supply their own ID), or generates a UUID4
    when the header is absent.  The ID is stored in the async-context
    via ``set_request_id()`` and echoed back in the response header so
    clients can correlate their requests with server-side log lines.

``LoggingMiddleware``
    Emits a structured log line for every HTTP request/response pair.

    Fields logged
    ~~~~~~~~~~~~~
    ``request_id``    — unique identifier for this request
    ``method``        — HTTP verb (``GET``, ``POST``, …)
    ``path``          — URL path (query string excluded from the log)
    ``status_code``   — HTTP response status code
    ``duration_ms``   — round-trip duration in milliseconds (2 d.p.)
    ``client_ip``     — remote address as reported by Starlette
    ``user_agent``    — ``User-Agent`` header value (truncated to 200
                        characters to prevent log bloat from
                        excessively long UA strings)

    The ``Authorization`` header is **never** logged.  Neither is the
    full ``headers`` mapping.  Only the safe subset listed above is
    extracted.

Ordering
--------
Middleware is applied in reverse registration order by Starlette, so
``RequestIDMiddleware`` must be added **after** ``LoggingMiddleware``
in ``main.py`` to ensure the request ID is set before the logging
middleware runs::

    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)   # runs first
"""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.constants import REQUEST_ID_HEADER
from app.core.request_context import set_request_id
from app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_MAX_USER_AGENT_LENGTH: int = 200


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assign and propagate a unique request identifier.

    If the client supplies an ``X-Request-ID`` header, that value is
    used as-is (useful for distributed tracing).  Otherwise a UUID4 is
    generated.  The identifier is:

    1. Stored in the ``ContextVar`` (via ``set_request_id``) so that
       every log line emitted during this request carries it.
    2. Echoed back to the client via the ``X-Request-ID`` response
       header.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Process the request, injecting and propagating the request ID."""
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        token = set_request_id(request_id)
        try:
            response = await call_next(request)
        finally:
            # Always reset the context var, even on exception, to prevent
            # context leakage between requests in the same async worker.
            from app.core.request_context import _request_id_ctx  # noqa: PLC0415

            _request_id_ctx.reset(token)

        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class LoggingMiddleware(BaseHTTPMiddleware):
    """Emit a structured JSON log line for every HTTP request.

    The log is emitted *after* the response is produced so that
    ``status_code`` and ``duration_ms`` are both available.

    Security note: only the specific fields listed in the module
    docstring are extracted from the request.  The full header dict
    and the ``Authorization`` header are never logged.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        """Log request metadata and delegate to the next handler."""
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        # Extract only the safe, non-sensitive fields we need.
        client_ip: str = request.client.host if request.client else "unknown"
        raw_ua: str = request.headers.get("user-agent", "")
        user_agent: str = raw_ua[:_MAX_USER_AGENT_LENGTH]

        logger.info(
            "HTTP %s %s → %s (%.2f ms)",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "http_method": request.method,
                "http_path": request.url.path,
                "http_status": response.status_code,
                "duration_ms": duration_ms,
                "client_ip": client_ip,
                "user_agent": user_agent,
            },
        )
        return response
