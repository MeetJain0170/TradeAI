"""TradeAI FastAPI application entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
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
    title="TradeAI API",
    description=(
        "Enterprise-grade, AI-native trading operating system combining "
        "multi-model forecasting, RAG, and a multi-agent decision system."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# ------------------------------------------------------------------ #
# OpenAPI Customization for JWT Bearer Authentication                 #
# ------------------------------------------------------------------ #


def custom_openapi() -> dict[str, object]:
    """Custom OpenAPI schema generator configuring HTTPBearer security scheme."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter JWT access token in the format: Bearer <token>",
        }
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]

# ------------------------------------------------------------------ #
# Middleware                                                           #
# ------------------------------------------------------------------ #

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
    """Convert any ``TradeAIError`` into the standard error envelope."""
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
    """Catch-all handler for unexpected exceptions."""
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

app.include_router(v1_router, prefix="/api")


@app.get("/health", response_model=HealthResponse, tags=["Infrastructure"])
async def health() -> HealthResponse:
    """Legacy health check for load balancers and Docker healthchecks."""
    return HealthResponse()
