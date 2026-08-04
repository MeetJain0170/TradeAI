"""Application configuration via Pydantic Settings.

All environment variables are declared here as typed fields.
No other module may call ``os.getenv`` directly; they must read
from the ``Settings`` instance returned by ``get_settings()``.

``pydantic-settings`` handles ``.env`` file loading natively — no
``python-dotenv`` import is required or used.
"""

from __future__ import annotations

import os
from enum import StrEnum
from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppEnvironment(StrEnum):
    """Valid deployment environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Centralised, validated application configuration.

    All values are read from environment variables (or a ``.env`` file
    at the project root).  Required fields raise a ``ValidationError``
    at import time if they are absent or invalid, causing a fast-fail
    before the server binds any port.
    """

    model_config = SettingsConfigDict(
        # Walk up from backend/config/ two levels to the repo root (.env lives there).
        env_file=os.path.join(os.path.dirname(__file__), "..", "..", ".env"),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ------------------------------------------------------------------ #
    # Application                                                          #
    # ------------------------------------------------------------------ #

    APP_ENV: AppEnvironment = Field(
        default=AppEnvironment.DEVELOPMENT,
        description="Deployment environment: development | staging | production.",
    )
    APP_DEBUG: bool = Field(
        default=False,
        description="Enable debug mode.  Must be False in production.",
    )

    # ------------------------------------------------------------------ #
    # Server                                                               #
    # ------------------------------------------------------------------ #

    HOST: str = Field(
        default="0.0.0.0",  # noqa: S104 — intentional for container binding
        description="Host address the Uvicorn server binds to.",
    )
    PORT: int = Field(
        default=8000,
        description="Port the Uvicorn server listens on.",
        gt=0,
        le=65535,
    )

    # ------------------------------------------------------------------ #
    # Logging                                                              #
    # ------------------------------------------------------------------ #

    LOG_LEVEL: str = Field(
        default="INFO",
        description="Root log level: DEBUG | INFO | WARNING | ERROR | CRITICAL.",
        pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
    )

    # ------------------------------------------------------------------ #
    # Database                                                             #
    # ------------------------------------------------------------------ #

    DATABASE_URL: str = Field(
        description=(
            "SQLAlchemy async database URL, e.g. "
            "postgresql+asyncpg://user:pass@host:5432/db"
        ),
    )

    # ------------------------------------------------------------------ #
    # Redis                                                                #
    # ------------------------------------------------------------------ #

    REDIS_URL: str = Field(
        description="Redis connection URL, e.g. redis://redis:6379/0",
    )

    # ------------------------------------------------------------------ #
    # Vector Database                                                      #
    # ------------------------------------------------------------------ #

    VECTOR_DB_URL: str = Field(
        description="Qdrant (or compatible) vector database URL.",
    )

    # ------------------------------------------------------------------ #
    # Authentication / JWT                                                 #
    # ------------------------------------------------------------------ #

    JWT_SECRET_KEY: SecretStr = Field(
        description=(
            "Secret used to sign JWT tokens.  Must be at least 32 characters "
            "and should be a cryptographically random string in staging/production."
        ),
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT signing algorithm.",
    )
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: Annotated[int, Field(gt=0)] = Field(
        default=30,
        description="Access token lifetime in minutes.",
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: Annotated[int, Field(gt=0)] = Field(
        default=7,
        description="Refresh token lifetime in days.",
    )

    # ------------------------------------------------------------------ #
    # LLM (optional — required only from Phase 9 onwards)                 #
    # ------------------------------------------------------------------ #

    OPENAI_API_KEY: SecretStr | None = Field(
        default=None,
        description="OpenAI-compatible API key.  Optional until the RAG/agents phase.",
    )

    # ------------------------------------------------------------------ #
    # Brokers (optional — required only from Phase 14 onwards)            #
    # ------------------------------------------------------------------ #

    UPSTOX_API_KEY: SecretStr | None = Field(
        default=None,
        description="Upstox API key.  Optional until the broker phase.",
    )
    UPSTOX_API_SECRET: SecretStr | None = Field(
        default=None,
        description="Upstox API secret.  Optional until the broker phase.",
    )
    ZERODHA_API_KEY: SecretStr | None = Field(
        default=None,
        description="Zerodha API key.  Optional until the broker phase.",
    )
    ZERODHA_API_SECRET: SecretStr | None = Field(
        default=None,
        description="Zerodha API secret.  Optional until the broker phase.",
    )

    # ------------------------------------------------------------------ #
    # Market Data (Phase 4)                                                #
    # ------------------------------------------------------------------ #

    MARKET_DATA_QUOTE_TTL_SECONDS: int = Field(
        default=30,
        description="Redis TTL in seconds for cached market quotes.",
        gt=0,
    )
    MARKET_DATA_INDICES_TTL_SECONDS: int = Field(
        default=60,
        description="Redis TTL in seconds for cached market indices.",
        gt=0,
    )
    MARKET_DATA_HISTORY_TTL_SECONDS: int = Field(
        default=300,
        description="Redis TTL in seconds for cached OHLCV history.",
        gt=0,
    )
    MARKET_DATA_OPTIONS_TTL_SECONDS: int = Field(
        default=30,
        description="Redis TTL in seconds for cached options chain.",
        gt=0,
    )
    MARKET_DATA_WATCHLIST: list[str] = Field(
        default=["AAPL", "MSFT", "NVDA", "RELIANCE.NS"],
        description=(
            "Symbols ingested by the Celery background task. "
            "Set via comma-separated env var: "
            "MARKET_DATA_WATCHLIST=AAPL,MSFT,NVDA"
        ),
    )

    # ------------------------------------------------------------------ #
    # Celery (Phase 4)                                                     #
    # ------------------------------------------------------------------ #

    CELERY_BROKER_URL: str = Field(
        default="redis://localhost:6379/1",
        description=(
            "Celery broker URL.  Uses Redis db=1 to avoid key collisions "
            "with auth JTI keys stored in db=0."
        ),
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://localhost:6379/1",
        description="Celery result backend URL.",
    )

    # ------------------------------------------------------------------ #
    # Validators                                                           #
    # ------------------------------------------------------------------ #

    @field_validator(
        "OPENAI_API_KEY",
        "UPSTOX_API_KEY",
        "UPSTOX_API_SECRET",
        "ZERODHA_API_KEY",
        "ZERODHA_API_SECRET",
        mode="before",
    )
    @classmethod
    def normalize_empty_optional_secrets(cls, value: object) -> object:
        """Convert empty strings or empty SecretStrs to None for optional API keys."""
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        if isinstance(value, SecretStr) and not value.get_secret_value().strip():
            return None
        return value

    @field_validator("JWT_SECRET_KEY", mode="before")
    @classmethod
    def jwt_secret_must_be_strong(cls, value: object) -> object:
        """Reject an absent or short JWT secret at startup.

        A minimum length of 32 characters is enforced so that trivially
        weak secrets (e.g. ``"123"`` or ``"secret"``) are caught before
        the server starts.
        """
        raw = str(value).strip() if value else ""
        if not raw:
            raise ValueError(
                "JWT_SECRET_KEY must not be empty. "
                "Set a cryptographically random secret in your .env file."
            )
        if len(raw) < 32:
            raise ValueError(
                f"JWT_SECRET_KEY must be at least 32 characters long "
                f"(got {len(raw)}).  Generate one with: "
                f'python -c "import secrets; print(secrets.token_hex(32))"'
            )
        return value

    # ------------------------------------------------------------------ #
    # Derived helpers                                                      #
    # ------------------------------------------------------------------ #

    @property
    def is_production(self) -> bool:
        """Return True when running in the production environment."""
        return self.APP_ENV == AppEnvironment.PRODUCTION

    @property
    def is_development(self) -> bool:
        """Return True when running in the development environment."""
        return self.APP_ENV == AppEnvironment.DEVELOPMENT

    @property
    def effective_log_level(self) -> str:
        """Return the effective log level.

        When ``APP_DEBUG`` is True the level is forced to ``DEBUG``
        regardless of the ``LOG_LEVEL`` setting.
        """
        return "DEBUG" if self.APP_DEBUG else self.LOG_LEVEL


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached application settings singleton.

    The instance is created once on first call and reused for the
    lifetime of the process.  Tests that need different values should
    call ``get_settings.cache_clear()`` before and after the test.
    """
    return Settings()  # type: ignore[call-arg]
