"""Custom exception hierarchy for TradeAI.

All application exceptions inherit from ``TradeAIError``.  Each
subclass declares a default HTTP status code and a standardised
machine-readable error code, which the global exception handler uses
to build the standardised API error response.

Hierarchy
---------
TradeAIError
├── ConfigurationError   (500 — startup/config issues)
├── ValidationError      (422 — bad input from callers)
├── InfrastructureError  (503 — downstream service failure)
├── AuthenticationError  (401 — missing/invalid credentials)
└── AuthorizationError   (403 — insufficient permissions)
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any


class TradeAIError(Exception):
    """Base exception for all TradeAI-specific errors."""

    default_http_status: int = HTTPStatus.INTERNAL_SERVER_ERROR.value
    default_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        details: dict[str, Any] | None = None,
        http_status: int | None = None,
    ) -> None:
        super().__init__(message)
        self.message: str = message
        self.code: str = code or self.default_code
        self.details: dict[str, Any] = details or {}
        self.http_status: int = http_status or self.default_http_status

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"{self.__class__.__name__}("
            f"message={self.message!r}, "
            f"code={self.code!r}, "
            f"http_status={self.http_status!r})"
        )


class ConfigurationError(TradeAIError):
    """Raised when application cannot start due to invalid config (500)."""

    default_http_status: int = HTTPStatus.INTERNAL_SERVER_ERROR.value
    default_code: str = "CONFIGURATION_ERROR"


class ValidationError(TradeAIError):
    """Raised when caller-supplied input fails business-rule validation.

    Distinct from Pydantic's ``ValidationError`` (which handles schema
    validation at the request boundary).  This exception is used inside
    service and domain layers where the input has already passed schema
    validation but violates a business rule.

    HTTP 422 — unprocessable entity; the request was well-formed but
    semantically invalid.
    """

    default_http_status: int = HTTPStatus.UNPROCESSABLE_ENTITY.value
    default_code: str = "VALIDATION_ERROR"


class InfrastructureError(TradeAIError):
    """Raised when external dependency is unavailable (503)."""

    default_http_status: int = HTTPStatus.SERVICE_UNAVAILABLE.value
    default_code: str = "INFRASTRUCTURE_ERROR"


class AuthenticationError(TradeAIError):
    """Raised when authentication fails (401)."""

    default_http_status: int = HTTPStatus.UNAUTHORIZED.value
    default_code: str = "AUTHENTICATION_ERROR"


class AuthorizationError(TradeAIError):
    """Raised when an authenticated user lacks required permissions (403)."""

    default_http_status: int = HTTPStatus.FORBIDDEN.value
    default_code: str = "FORBIDDEN"
