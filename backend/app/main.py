"""TradeAI FastAPI application entry point.

This module is intentionally minimal.  Its only responsibilities are:

1. Instantiate the ``FastAPI`` application with the correct metadata
   and lifespan context.
2. Register middleware (order matters — see note below).
3. Register global exception handlers.
4. Mount the health endpoint.

All business logic, configuration, logging, and infrastructure
initialisation belong in their respective modules, not here.

Middleware registration order
------------------------------
Starlette applies middleware in **reverse** registration order, so the
last-added middleware runs first.  We register:

    app.add_middleware(LoggingMiddleware)    # runs second
    app.add_middleware(RequestIDMiddleware)  # runs first

This ensures the request ID is set in the ``ContextVar`` before the
logging middleware reads it.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import TradeAIError
from app.core.lifespan import lifespan
from app.core.middleware import LoggingMiddleware, RequestIDMiddleware
from app.core.request_context import get_request_id
from app.core.responses import ErrorResponse
from app.domain.schemas.health import HealthResponse

# ------------------------------------------------------------------ #
# Application                                                         #
# ------------------------------------------------------------------ #

app = FastAPI(
    title="TradeAI",
    description=(
        "Enterprise-grade, AI-native trading operating system combining "
        "multi-model forecasting, RAG, and a multi-agent decision system."
    ),
    version="0.1.0",
    lifespan=lifespan,
    # Disable the default exception handlers so our custom ones take over.
    # (FastAPI still registers validation error handlers internally.)
)

# ------------------------------------------------------------------ #
# Middleware                                                           #
# ------------------------------------------------------------------ #

# Registered in reverse-execution order (last registered = first executed).
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestIDMiddleware)

# ------------------------------------------------------------------ #
# Exception handlers                                                  #
# ------------------------------------------------------------------ #

_logger = logging.getLogger(__name__)


@app.exception_handler(TradeAIError)
async def tradeai_error_handler(
    request: Request,
    exc: TradeAIError,
) -> JSONResponse:
    """Convert any ``TradeAIError`` (and subclass) into the standard
    error envelope.

    The exception is logged at ERROR level so it appears in structured
    logs with the current ``request_id``.  The stack trace is included
    in the log but is **never** sent to the client.
    """
    _logger.error(
        "TradeAI error: %s",
        exc.message,
        exc_info=exc,
        extra={"error_code": exc.code, "http_status": exc.http_status},
    )
    body = ErrorResponse.from_exception(
        code=exc.code,
        message=exc.message,
        request_id=get_request_id(),
    )
    return JSONResponse(
        status_code=exc.http_status,
        content=body.model_dump(),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """Catch-all handler for unexpected exceptions.

    Logs the full traceback server-side and returns a generic 500
    response.  The raw exception message is intentionally suppressed
    from the client response to avoid leaking internal implementation
    details.
    """
    _logger.critical(
        "Unhandled exception",
        exc_info=exc,
        extra={"path": request.url.path, "method": request.method},
    )
    body = ErrorResponse.from_exception(
        code="INTERNAL_ERROR",
        message="An unexpected error occurred. Please try again later.",
        request_id=get_request_id(),
    )
    return JSONResponse(
        status_code=500,
        content=body.model_dump(),
    )


# ------------------------------------------------------------------ #
# Routes                                                              #
# ------------------------------------------------------------------ #


@app.get("/health", response_model=HealthResponse, tags=["Infrastructure"])
async def health() -> HealthResponse:
    """Health check endpoint for load balancers and Docker healthchecks."""
    return HealthResponse()
