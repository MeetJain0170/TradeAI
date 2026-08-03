"""Alembic async migration environment.

This file configures Alembic for async SQLAlchemy usage with PostgreSQL.
It reads the database URL from ``config.settings.get_settings()`` at runtime
so that the same ``.env`` file drives both the application and migrations.

Usage
-----
::

    # Apply all pending migrations
    uv run alembic upgrade head

    # Rollback all migrations
    uv run alembic downgrade base

    # Autogenerate a new migration
    uv run alembic revision --autogenerate -m "describe_your_change"
"""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from logging.config import fileConfig

import app.infrastructure.database.models  # noqa: F401 — registers all ORM models
from alembic import context

# Import the declarative Base so Alembic can inspect all registered models.
from app.infrastructure.database.base import Base
from config.settings import get_settings
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlalchemy.pool import NullPool

# ---------------------------------------------------------------------------
# Alembic config object
# ---------------------------------------------------------------------------

config = context.config

# Inject structured logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override the sqlalchemy.url from alembic.ini with the runtime settings URL.
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Provide the metadata for autogenerate support.
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Offline migrations (generate SQL without a live connection)
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online migrations (apply against a live async connection)
# ---------------------------------------------------------------------------


def do_run_migrations(connection: object) -> None:
    """Configure context and run all pending migrations."""
    context.configure(
        connection=connection,  # type: ignore[arg-type]
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run all pending migrations."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online (live database) migrations."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        # If called from within an existing event loop (e.g. async pytest fixture),
        # run the async migration in a thread so asyncio.run() doesn't conflict.
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(lambda: asyncio.run(run_async_migrations()))
            future.result()
    else:
        asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
