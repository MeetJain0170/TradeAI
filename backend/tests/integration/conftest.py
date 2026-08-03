"""Integration test fixtures for the database layer.

Strategy
--------
Uses the database URL configured via environment variables (or settings).
Does NOT programmatically create or drop databases. Runs Alembic migrations
on the configured database engine.

Uses NullPool for the test engine so every test session/connection is isolated
without connection reuse artifacts across async test loops.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator

import pytest
from alembic import command
from alembic.config import Config
from config.settings import get_settings
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool


@pytest.fixture(scope="session")
def test_db_url() -> str:
    """Resolve database URL for integration tests."""
    return os.getenv(
        "TEST_DATABASE_URL",
        get_settings().DATABASE_URL,
    )


@pytest.fixture(scope="session")
async def test_engine(test_db_url: str) -> AsyncGenerator[AsyncEngine]:
    """Provide a session-scoped AsyncEngine and ensure migrations are applied."""
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_db_url)
    command.upgrade(alembic_cfg, "head")

    engine = create_async_engine(test_db_url, poolclass=NullPool, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(test_engine: AsyncEngine) -> AsyncGenerator[AsyncSession]:
    """Yield an AsyncSession inside a transaction that is rolled back after the test."""
    session_factory = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        transaction = await session.begin()
        try:
            yield session
        finally:
            if transaction.is_active:
                await transaction.rollback()
