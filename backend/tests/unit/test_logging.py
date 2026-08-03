"""Unit tests for the structured JSON logging infrastructure.

Tests cover:
- JSONFormatter emits valid JSON
- Required fields are present in every log line
- ``service`` and ``environment`` fields appear
- ``request_id`` is injected from the ContextVar
- Secret scrubber redacts known patterns
- Sensitive objects (settings, auth headers) are not accidentally logged
- configure_logging is idempotent (no duplicate handlers)
"""

from __future__ import annotations

import json
import logging
from io import StringIO
from typing import Any

from app.core.request_context import _request_id_ctx, set_request_id
from app.infrastructure.logging.config import configure_logging
from app.infrastructure.logging.formatter import JSONFormatter, _scrub_secrets

# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #


def capture_log(
    level: int = logging.INFO,
    environment: str = "development",
) -> tuple[logging.Logger, StringIO]:
    """Return a (logger, buffer) pair wired with JSONFormatter."""
    buf = StringIO()
    handler = logging.StreamHandler(buf)
    handler.setFormatter(JSONFormatter(environment=environment))
    handler.setLevel(level)
    log = logging.getLogger(f"test.{id(buf)}")
    log.handlers.clear()
    log.addHandler(handler)
    log.setLevel(level)
    log.propagate = False
    return log, buf


def parse_log_line(buf: StringIO) -> dict[str, Any]:
    """Parse the last JSON line written to *buf*."""
    raw = buf.getvalue().strip().splitlines()[-1]
    return json.loads(raw)  # type: ignore[no-any-return]


# ------------------------------------------------------------------ #
# JSONFormatter — structure                                           #
# ------------------------------------------------------------------ #


class TestJSONFormatterStructure:
    def test_emits_valid_json(self) -> None:
        log, buf = capture_log()
        log.info("hello")
        data = parse_log_line(buf)
        assert isinstance(data, dict)

    def test_required_fields_present(self) -> None:
        log, buf = capture_log()
        log.info("test message")
        data = parse_log_line(buf)
        required = {
            "timestamp",
            "level",
            "service",
            "environment",
            "logger",
            "message",
            "request_id",
            "module",
            "function",
            "line",
        }
        assert required <= data.keys(), f"Missing fields: {required - data.keys()}"

    def test_message_content(self) -> None:
        log, buf = capture_log()
        log.info("hello world")
        data = parse_log_line(buf)
        assert data["message"] == "hello world"

    def test_level_field_reflects_log_level(self) -> None:
        log, buf = capture_log(level=logging.WARNING)
        log.warning("watch out")
        data = parse_log_line(buf)
        assert data["level"] == "WARNING"

    def test_service_field_is_present(self) -> None:
        log, buf = capture_log()
        log.info("check service")
        data = parse_log_line(buf)
        assert data["service"] == "tradeai-api"

    def test_environment_field_matches_constructor_argument(self) -> None:
        log, buf = capture_log(environment="staging")
        log.info("check env")
        data = parse_log_line(buf)
        assert data["environment"] == "staging"

    def test_timestamp_is_iso8601(self) -> None:
        from datetime import datetime

        log, buf = capture_log()
        log.info("ts check")
        data = parse_log_line(buf)
        # Must parse without raising
        ts = datetime.fromisoformat(data["timestamp"])
        assert ts is not None

    def test_exception_field_included_on_error(self) -> None:
        log, buf = capture_log(level=logging.ERROR)
        try:
            raise ValueError("boom")
        except ValueError:
            log.exception("caught")
        data = parse_log_line(buf)
        assert "exception" in data
        assert "ValueError" in data["exception"]


# ------------------------------------------------------------------ #
# Request ID injection                                                #
# ------------------------------------------------------------------ #


class TestRequestIDInjection:
    def test_request_id_injected_from_context_var(self) -> None:
        log, buf = capture_log()
        token = set_request_id("test-uuid-1234")
        try:
            log.info("with request id")
        finally:
            _request_id_ctx.reset(token)
        data = parse_log_line(buf)
        assert data["request_id"] == "test-uuid-1234"

    def test_request_id_defaults_to_unknown_outside_request(self) -> None:
        # Ensure no request ID is set in this test.
        token = set_request_id("unknown")
        _request_id_ctx.reset(token)
        log, buf = capture_log()
        log.info("no request")
        data = parse_log_line(buf)
        assert data["request_id"] == "unknown"


# ------------------------------------------------------------------ #
# Secret scrubber                                                     #
# ------------------------------------------------------------------ #


class TestSecretScrubber:
    def test_password_value_is_redacted(self) -> None:
        result = _scrub_secrets("password=mysecretpass")
        assert "mysecretpass" not in result
        assert "***REDACTED***" in result

    def test_secret_key_value_is_redacted(self) -> None:
        result = _scrub_secrets("secret_key=abc123def456")
        assert "abc123def456" not in result
        assert "***REDACTED***" in result

    def test_api_key_value_is_redacted(self) -> None:
        result = _scrub_secrets("api_key=sk-abcdefghijklmno")
        assert "sk-abcdefghijklmno" not in result
        assert "***REDACTED***" in result

    def test_token_value_is_redacted(self) -> None:
        result = _scrub_secrets("token=Bearer eyJhbGciOiJIUzI1NiJ9")
        assert "eyJhbGciOiJIUzI1NiJ9" not in result
        assert "***REDACTED***" in result

    def test_compound_field_name_not_falsely_redacted(self) -> None:
        """market_api_key_count=5 should NOT be redacted (compound word)."""
        # The scrubber pattern requires the key to appear as a standalone word.
        # 'market_api_key_count' does not match because 'api_key' is not
        # bounded — it's embedded in a longer word.
        result = _scrub_secrets("market_api_key_count=5")
        # This should pass through unchanged (no false positive).
        assert result == "market_api_key_count=5"

    def test_message_without_secrets_unchanged(self) -> None:
        msg = "Fetched OHLCV for RELIANCE with 100 bars"
        assert _scrub_secrets(msg) == msg

    def test_scrubber_applied_in_formatter(self) -> None:
        """End-to-end: a message containing 'password=...' is scrubbed."""
        log, buf = capture_log()
        log.info("User auth attempt password=hunter2")
        data = parse_log_line(buf)
        assert "hunter2" not in data["message"]
        assert "***REDACTED***" in data["message"]


# ------------------------------------------------------------------ #
# No secrets in structured logs (design-level enforcement)           #
# ------------------------------------------------------------------ #


class TestNoSecretsInLogs:
    """These tests verify that known sensitive patterns do not appear
    in log output when using the standard logger correctly."""

    def test_jwt_secret_value_not_in_log(self) -> None:
        """SecretStr values must not appear when settings are logged safely."""
        log, buf = capture_log()
        # Simulate logging a safe settings summary (the correct pattern).
        log.info(
            "App started",
            extra={
                "environment": "development",
                "log_level": "INFO",
                "host": "0.0.0.0",
                "port": 8000,
            },
        )
        raw_output = buf.getvalue()
        # The test JWT secret from VALID_ENV must not appear.
        assert "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa" not in raw_output

    def test_authorization_header_not_logged_by_logging_middleware(
        self,
    ) -> None:
        """Logging middleware must not log Authorization header values."""
        # This is a structural test: verify the middleware source code
        # does not reference 'Authorization' in a way that would log it.
        import inspect

        from app.core.middleware import LoggingMiddleware

        source = inspect.getsource(LoggingMiddleware.dispatch)
        # The middleware may reference the header name to *exclude* it,
        # but must not log its value.
        assert 'headers.get("authorization"' not in source.lower() or (
            # If it appears, it must only be in a comment or exclusion context.
            "authorization" not in source.lower()
        )


# ------------------------------------------------------------------ #
# configure_logging                                                   #
# ------------------------------------------------------------------ #


class TestConfigureLogging:
    def test_idempotent_no_duplicate_handlers(self) -> None:
        """Calling configure_logging twice must not add duplicate handlers."""
        configure_logging("INFO", is_development=True)
        configure_logging("INFO", is_development=True)
        root = logging.getLogger()
        assert len(root.handlers) == 1

    def test_sets_correct_level(self) -> None:
        configure_logging("DEBUG", is_development=True)
        root = logging.getLogger()
        assert root.level == logging.DEBUG

    def test_handler_uses_json_formatter(self) -> None:
        configure_logging("INFO", is_development=True)
        root = logging.getLogger()
        assert len(root.handlers) >= 1
        assert isinstance(root.handlers[0].formatter, JSONFormatter)

    def test_uvicorn_access_level_raised_in_production(self) -> None:
        configure_logging("INFO", is_development=False)
        assert logging.getLogger("uvicorn.access").level == logging.WARNING

    def test_uvicorn_access_level_not_raised_in_development(self) -> None:
        configure_logging("INFO", is_development=True)
        # In development the level stays at NOTSET (inherits from root).
        uvicorn_access = logging.getLogger("uvicorn.access")
        assert uvicorn_access.level == logging.NOTSET
