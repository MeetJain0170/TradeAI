"""Custom exception hierarchy for TradeAI.

All application exceptions inherit from ``TradeAIError``.  Each
subclass declares a default HTTP status code and a standardised
machine-readable error code, which the global exception handler uses
to build the standardised API error response.

Error codes are uppercase constants so that clients can reliably
switch on them and future exception types follow the same pattern.

Hierarchy
---------
TradeAIError
├── ConfigurationError   (500 — startup/config issues)
├── ValidationError      (422 — bad input from callers)
├── InfrastructureError  (503 — downstream service failure)
└── AuthenticationError  (401 — missing/invalid credentials)
"""

from __future__ import annotations

from http import HTTPStatus
from typing import Any


class TradeAIError(Exception):
    """Base exception for all TradeAI-specific errors.

    Parameters
    ----------
    message:
        Human-readable description of what went wrong.
    code:
        Machine-readable UPPER_SNAKE_CASE identifier used in API error
        responses.  Defaults to the subclass ``default_code``.
    details:
        Optional mapping of additional context to include in the error
        response (e.g., field names, upstream error codes).  Must not
        contain secrets or PII.
    http_status:
        HTTP status code to return when this exception propagates to the
        API layer.  Subclasses set a class-level default; callers may
        supply a per-instance override.
    """

    #: Default HTTP status code for this exception family.
    default_http_status: int = HTTPStatus.INTERNAL_SERVER_ERROR.value

    #: Standardised machine-readable error code (UPPER_SNAKE_CASE).
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
    """Raised when the application cannot start due to invalid or missing
    configuration (e.g., absent required environment variable).

    HTTP 500 — indicates a deployment problem, not a client error.
    """

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
    """Raised when an external dependency (database, Redis, broker API,
    vector DB, LLM provider) is unavailable or returns an unexpected error.

    HTTP 503 — service temporarily unavailable.
    """

    default_http_status: int = HTTPStatus.SERVICE_UNAVAILABLE.value
    default_code: str = "INFRASTRUCTURE_ERROR"


class AuthenticationError(TradeAIError):
    """Raised when authentication fails — missing, invalid, or expired
    credentials.

    HTTP 401 — unauthorised.
    """

    default_http_status: int = HTTPStatus.UNAUTHORIZED.value
    default_code: str = "AUTHENTICATION_ERROR"
