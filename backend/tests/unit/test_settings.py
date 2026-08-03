"""Unit tests for backend/config/settings.py.

Tests cover:
- Happy-path loading from environment variables
- Validation failures for missing/invalid required fields
- JWT_SECRET_KEY length enforcement
- APP_ENV enum validation
- Singleton caching behaviour
- No ``os.getenv`` usage outside settings.py
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from config.settings import AppEnvironment, Settings, get_settings
from pydantic import ValidationError as PydanticValidationError

# ------------------------------------------------------------------ #
# Helpers                                                             #
# ------------------------------------------------------------------ #

VALID_ENV: dict[str, str] = {
    "APP_ENV": "development",
    "APP_DEBUG": "false",
    "DATABASE_URL": "postgresql+asyncpg://u:p@localhost:5432/db",
    "REDIS_URL": "redis://localhost:6379/0",
    "VECTOR_DB_URL": "http://localhost:6333",
    "JWT_SECRET_KEY": "a" * 32,  # exactly minimum length
    "JWT_ALGORITHM": "HS256",
    "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    "JWT_REFRESH_TOKEN_EXPIRE_DAYS": "7",
    "LOG_LEVEL": "INFO",
    "HOST": "0.0.0.0",
    "PORT": "8000",
}


def make_settings(**overrides: Any) -> Settings:
    """Construct a ``Settings`` instance with controlled env values.

    Uses Pydantic Settings' ``_env_file=None`` trick combined with
    explicit kwargs so tests are hermetic and do not read the real
    ``.env``.
    """
    env = {**VALID_ENV, **overrides}
    # Remove None-valued overrides so absent optionals use their defaults.
    env = {k: v for k, v in env.items() if v is not None}
    return Settings(_env_file=None, **env)  # type: ignore[call-arg]


# ------------------------------------------------------------------ #
# Happy-path tests                                                    #
# ------------------------------------------------------------------ #


class TestSettingsHappyPath:
    def test_defaults_load_from_explicit_values(self) -> None:
        """Settings correctly stores all provided valid values."""
        s = make_settings()
        assert s.APP_ENV == AppEnvironment.DEVELOPMENT
        assert s.APP_DEBUG is False
        assert s.DATABASE_URL == "postgresql+asyncpg://u:p@localhost:5432/db"
        assert s.REDIS_URL == "redis://localhost:6379/0"
        assert s.VECTOR_DB_URL == "http://localhost:6333"
        assert s.JWT_ALGORITHM == "HS256"
        assert s.JWT_ACCESS_TOKEN_EXPIRE_MINUTES == 30
        assert s.JWT_REFRESH_TOKEN_EXPIRE_DAYS == 7
        assert s.LOG_LEVEL == "INFO"
        assert s.HOST == "0.0.0.0"
        assert s.PORT == 8000

    def test_app_env_production(self) -> None:
        s = make_settings(APP_ENV="production")
        assert s.APP_ENV == AppEnvironment.PRODUCTION
        assert s.is_production is True
        assert s.is_development is False

    def test_app_env_staging(self) -> None:
        s = make_settings(APP_ENV="staging")
        assert s.APP_ENV == AppEnvironment.STAGING

    def test_effective_log_level_debug_overrides_log_level(self) -> None:
        """When APP_DEBUG is True, effective_log_level returns DEBUG."""
        s = make_settings(APP_DEBUG="true", LOG_LEVEL="WARNING")
        assert s.effective_log_level == "DEBUG"

    def test_effective_log_level_respects_log_level_when_not_debug(self) -> None:
        s = make_settings(APP_DEBUG="false", LOG_LEVEL="WARNING")
        assert s.effective_log_level == "WARNING"

    def test_jwt_secret_key_stored_as_secret_str(self) -> None:
        """SecretStr must never expose the raw value via str()."""
        s = make_settings()
        # Pydantic SecretStr repr hides the value.
        assert "a" * 32 not in str(s.JWT_SECRET_KEY)
        assert s.JWT_SECRET_KEY.get_secret_value() == "a" * 32

    def test_optional_llm_key_defaults_none(self) -> None:
        s = make_settings()
        assert s.OPENAI_API_KEY is None

    def test_optional_llm_key_empty_string_normalized_to_none(self) -> None:
        s = make_settings(OPENAI_API_KEY="")
        assert s.OPENAI_API_KEY is None

    def test_optional_broker_keys_default_none(self) -> None:
        s = make_settings()
        assert s.UPSTOX_API_KEY is None
        assert s.UPSTOX_API_SECRET is None
        assert s.ZERODHA_API_KEY is None
        assert s.ZERODHA_API_SECRET is None

    def test_optional_broker_keys_empty_string_normalized_to_none(self) -> None:
        s = make_settings(
            UPSTOX_API_KEY="",
            UPSTOX_API_SECRET="  ",
            ZERODHA_API_KEY="",
            ZERODHA_API_SECRET="",
        )
        assert s.UPSTOX_API_KEY is None
        assert s.UPSTOX_API_SECRET is None
        assert s.ZERODHA_API_KEY is None
        assert s.ZERODHA_API_SECRET is None


# ------------------------------------------------------------------ #
# Validation failure tests                                            #
# ------------------------------------------------------------------ #


class TestSettingsValidation:
    def test_invalid_app_env_raises(self) -> None:
        """Unknown APP_ENV value must raise ValidationError."""
        with pytest.raises(PydanticValidationError):
            make_settings(APP_ENV="invalid_env")

    def test_empty_jwt_secret_raises(self) -> None:
        """Empty JWT_SECRET_KEY must be rejected at startup."""
        with pytest.raises(PydanticValidationError) as exc_info:
            make_settings(JWT_SECRET_KEY="")
        assert "JWT_SECRET_KEY" in str(exc_info.value)

    def test_short_jwt_secret_raises(self) -> None:
        """JWT_SECRET_KEY shorter than 32 characters must be rejected."""
        with pytest.raises(PydanticValidationError) as exc_info:
            make_settings(JWT_SECRET_KEY="short")
        assert "32" in str(exc_info.value)

    def test_jwt_secret_exactly_32_chars_is_accepted(self) -> None:
        """JWT_SECRET_KEY of exactly 32 characters must be accepted."""
        s = make_settings(JWT_SECRET_KEY="x" * 32)
        assert s.JWT_SECRET_KEY.get_secret_value() == "x" * 32

    def test_invalid_log_level_raises(self) -> None:
        """LOG_LEVEL must be one of the recognised level names."""
        with pytest.raises(PydanticValidationError):
            make_settings(LOG_LEVEL="VERBOSE")

    def test_port_out_of_range_raises(self) -> None:
        """PORT must be in the valid TCP port range."""
        with pytest.raises(PydanticValidationError):
            make_settings(PORT="99999")


# ------------------------------------------------------------------ #
# Caching tests                                                       #
# ------------------------------------------------------------------ #


class TestSettingsCaching:
    def test_get_settings_returns_same_object(self) -> None:
        """``get_settings`` must be cached — same object on repeated calls."""
        get_settings.cache_clear()
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_cache_clear_allows_new_instance(self) -> None:
        """After ``cache_clear``, ``get_settings`` builds a fresh instance."""
        get_settings.cache_clear()
        s1 = get_settings()
        get_settings.cache_clear()
        s2 = get_settings()
        # Different objects (though equal in value when env hasn't changed).
        assert s1 is not s2


# ------------------------------------------------------------------ #
# No os.getenv outside settings.py                                   #
# ------------------------------------------------------------------ #


class TestNoDirectOsGetenv:
    """Ensure no application module (outside config/settings.py)
    calls ``os.getenv`` directly.

    This test scans source files to detect violations of the rule that
    all environment variable access must go through ``Settings``.
    """

    EXCLUDED_FILES = {"settings.py", "conftest.py"}

    def _collect_python_files(self) -> list[str]:
        """Collect all .py files under backend/ excluding settings.py."""
        root = os.path.join(os.path.dirname(__file__), "..", "..", "..", "app")
        root = os.path.normpath(root)
        result: list[str] = []
        for dirpath, _dirs, filenames in os.walk(root):
            for filename in filenames:
                if filename.endswith(".py") and filename not in self.EXCLUDED_FILES:
                    result.append(os.path.join(dirpath, filename))
        return result

    def test_no_os_getenv_in_app_modules(self) -> None:
        """No file under app/ may call os.getenv directly."""
        violations: list[str] = []
        for filepath in self._collect_python_files():
            with open(filepath, encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, start=1):
                    if "os.getenv" in line and not line.strip().startswith("#"):
                        violations.append(f"{filepath}:{lineno}")
        assert violations == [], (
            "Found os.getenv() calls outside config/settings.py:\n"
            + "\n".join(violations)
        )
