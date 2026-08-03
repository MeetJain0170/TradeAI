"""Unit tests for the custom exception hierarchy and global exception handlers.

Tests cover:
- Exception inheritance: all custom exceptions inherit from TradeAIError
- Default HTTP status codes per exception class
- Default error codes (UPPER_SNAKE_CASE) per exception class
- Custom code/http_status overrides work correctly
- Global exception handler returns the standardised error envelope
- Unhandled exceptions return HTTP 500 with the error envelope
- Stack traces are never sent to the client
"""

from __future__ import annotations

from http import HTTPStatus

from app.core.exceptions import (
    AuthenticationError,
    ConfigurationError,
    InfrastructureError,
    TradeAIError,
    ValidationError,
)
from app.core.responses import ErrorResponse
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app, raise_server_exceptions=False)


# ------------------------------------------------------------------ #
# Exception hierarchy                                                 #
# ------------------------------------------------------------------ #


class TestExceptionHierarchy:
    def test_configuration_error_inherits_tradeai_error(self) -> None:
        assert issubclass(ConfigurationError, TradeAIError)

    def test_validation_error_inherits_tradeai_error(self) -> None:
        assert issubclass(ValidationError, TradeAIError)

    def test_infrastructure_error_inherits_tradeai_error(self) -> None:
        assert issubclass(InfrastructureError, TradeAIError)

    def test_authentication_error_inherits_tradeai_error(self) -> None:
        assert issubclass(AuthenticationError, TradeAIError)

    def test_all_custom_exceptions_are_base_exception_subclass(self) -> None:
        for exc_cls in (
            TradeAIError,
            ConfigurationError,
            ValidationError,
            InfrastructureError,
            AuthenticationError,
        ):
            assert issubclass(exc_cls, Exception)


# ------------------------------------------------------------------ #
# HTTP status codes                                                   #
# ------------------------------------------------------------------ #


class TestHTTPStatusCodes:
    def test_tradeai_error_default_status_500(self) -> None:
        exc = TradeAIError("base")
        assert exc.http_status == HTTPStatus.INTERNAL_SERVER_ERROR.value

    def test_configuration_error_status_500(self) -> None:
        exc = ConfigurationError("config problem")
        assert exc.http_status == HTTPStatus.INTERNAL_SERVER_ERROR.value

    def test_validation_error_status_422(self) -> None:
        exc = ValidationError("bad input")
        assert exc.http_status == HTTPStatus.UNPROCESSABLE_ENTITY.value

    def test_infrastructure_error_status_503(self) -> None:
        exc = InfrastructureError("db down")
        assert exc.http_status == HTTPStatus.SERVICE_UNAVAILABLE.value

    def test_authentication_error_status_401(self) -> None:
        exc = AuthenticationError("invalid token")
        assert exc.http_status == HTTPStatus.UNAUTHORIZED.value

    def test_per_instance_http_status_override(self) -> None:
        exc = ValidationError("conflict", http_status=409)
        assert exc.http_status == 409


# ------------------------------------------------------------------ #
# Error codes                                                         #
# ------------------------------------------------------------------ #


class TestErrorCodes:
    def test_tradeai_error_default_code(self) -> None:
        exc = TradeAIError("base")
        assert exc.code == "INTERNAL_ERROR"

    def test_configuration_error_code(self) -> None:
        exc = ConfigurationError("cfg")
        assert exc.code == "CONFIGURATION_ERROR"

    def test_validation_error_code(self) -> None:
        exc = ValidationError("val")
        assert exc.code == "VALIDATION_ERROR"

    def test_infrastructure_error_code(self) -> None:
        exc = InfrastructureError("infra")
        assert exc.code == "INFRASTRUCTURE_ERROR"

    def test_authentication_error_code(self) -> None:
        exc = AuthenticationError("auth")
        assert exc.code == "AUTHENTICATION_ERROR"

    def test_per_instance_code_override(self) -> None:
        exc = ValidationError("custom", code="SYMBOL_NOT_FOUND")
        assert exc.code == "SYMBOL_NOT_FOUND"


# ------------------------------------------------------------------ #
# Exception attributes                                                #
# ------------------------------------------------------------------ #


class TestExceptionAttributes:
    def test_message_stored(self) -> None:
        exc = ValidationError("the message")
        assert exc.message == "the message"
        assert str(exc) == "the message"

    def test_details_defaults_empty_dict(self) -> None:
        exc = ValidationError("x")
        assert exc.details == {}

    def test_details_stored(self) -> None:
        exc = ValidationError("x", details={"field": "symbol"})
        assert exc.details == {"field": "symbol"}


# ------------------------------------------------------------------ #
# Error response model                                                #
# ------------------------------------------------------------------ #


class TestErrorResponseModel:
    def test_from_exception_factory(self) -> None:
        resp = ErrorResponse.from_exception(
            code="VALIDATION_ERROR",
            message="Symbol required",
            request_id="req-123",
        )
        assert resp.success is False
        assert resp.error.code == "VALIDATION_ERROR"
        assert resp.error.message == "Symbol required"
        assert resp.error.request_id == "req-123"

    def test_serialised_success_is_false(self) -> None:
        resp = ErrorResponse.from_exception(
            code="INTERNAL_ERROR",
            message="Oops",
            request_id="r",
        )
        dumped = resp.model_dump()
        assert dumped["success"] is False
        assert "error" in dumped


# ------------------------------------------------------------------ #
# Global exception handler — API integration                         #
# ------------------------------------------------------------------ #

# We add temporary test routes to the app.  Each route raises a specific
# exception so we can verify the handler returns the correct response.

from fastapi import APIRouter  # noqa: E402

_test_router = APIRouter(prefix="/test-exc", include_in_schema=False)


@_test_router.get("/configuration")
async def _raise_configuration() -> None:
    raise ConfigurationError("Settings misconfigured")


@_test_router.get("/validation")
async def _raise_validation() -> None:
    raise ValidationError("Symbol is required")


@_test_router.get("/infrastructure")
async def _raise_infrastructure() -> None:
    raise InfrastructureError("Database unreachable")


@_test_router.get("/authentication")
async def _raise_authentication() -> None:
    raise AuthenticationError("Token expired")


@_test_router.get("/unhandled")
async def _raise_unhandled() -> None:
    raise RuntimeError("Something exploded")


app.include_router(_test_router)


class TestExceptionHandlerIntegration:
    def test_configuration_error_returns_500(self) -> None:
        resp = client.get("/test-exc/configuration")
        assert resp.status_code == 500

    def test_configuration_error_returns_error_envelope(self) -> None:
        resp = client.get("/test-exc/configuration")
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "CONFIGURATION_ERROR"
        assert "request_id" in body["error"]

    def test_validation_error_returns_422(self) -> None:
        resp = client.get("/test-exc/validation")
        assert resp.status_code == 422

    def test_validation_error_returns_error_envelope(self) -> None:
        resp = client.get("/test-exc/validation")
        body = resp.json()
        assert body["error"]["code"] == "VALIDATION_ERROR"
        assert body["error"]["message"] == "Symbol is required"

    def test_infrastructure_error_returns_503(self) -> None:
        resp = client.get("/test-exc/infrastructure")
        assert resp.status_code == 503

    def test_authentication_error_returns_401(self) -> None:
        resp = client.get("/test-exc/authentication")
        assert resp.status_code == 401

    def test_unhandled_exception_returns_500(self) -> None:
        resp = client.get("/test-exc/unhandled")
        assert resp.status_code == 500

    def test_unhandled_exception_returns_error_envelope(self) -> None:
        resp = client.get("/test-exc/unhandled")
        body = resp.json()
        assert body["success"] is False
        assert body["error"]["code"] == "INTERNAL_ERROR"
        assert "request_id" in body["error"]

    def test_raw_stack_trace_never_sent_to_client(self) -> None:
        """The client response must never contain a Python traceback."""
        for path in ("/test-exc/unhandled", "/test-exc/configuration"):
            resp = client.get(path)
            raw = resp.text
            assert "Traceback" not in raw, (
                f"Stack trace leaked in response for {path}"
            )
            assert "RuntimeError" not in raw or path != "/test-exc/unhandled"

    def test_error_response_contains_request_id(self) -> None:
        """Every error response must carry a request_id field."""
        resp = client.get("/test-exc/validation")
        body = resp.json()
        request_id = body["error"]["request_id"]
        assert isinstance(request_id, str)
        assert len(request_id) > 0

    def test_x_request_id_header_present_in_response(self) -> None:
        """The X-Request-ID header must be echoed back in error responses."""
        resp = client.get(
            "/test-exc/validation",
            headers={"X-Request-ID": "my-trace-id"},
        )
        assert resp.headers.get("x-request-id") == "my-trace-id"
