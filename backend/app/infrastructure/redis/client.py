"""Redis async connection manager and security data store.

Provides connection pool management, refresh token JTI revocation tracking,
and sliding-window rate limiting.

Failure strategy
----------------
* **Development / staging**: Redis failures are logged as warnings and the
  operation degrades gracefully (fail-open for rate limiting, fail-safe for
  JTI checks).  This keeps local development smooth when Redis is not running.
* **Production**: Redis is treated as a hard dependency for all auth-related
  operations.  Failures raise ``InfrastructureError`` so callers surface them
  as 503 responses rather than silently bypassing security controls.
"""

from __future__ import annotations

import os
import time
from typing import Any

from config.settings import get_settings
from redis.asyncio import ConnectionPool, Redis, RedisError

from app.core.exceptions import InfrastructureError
from app.infrastructure.logging.logger import get_logger

logger = get_logger(__name__)

_pool: ConnectionPool | None = None
_client: Redis | None = None


def _resolve_redis_url(raw_url: str) -> str:
    """Translate Docker-internal hostname to localhost when running outside a container.

    ``/.dockerenv`` is a zero-byte file created by Docker inside every
    container — its presence is a reliable indicator that the process is
    running inside Docker.  When absent we assume a local developer machine
    and substitute the container service hostname ``redis`` with
    ``localhost`` so the port-forwarded Redis is reachable.
    """
    is_in_docker = os.path.exists("/.dockerenv")
    if not is_in_docker and "redis://redis:" in raw_url:
        return raw_url.replace("redis://redis:", "redis://localhost:")
    return raw_url


def get_redis_client() -> Redis:
    """Return the global async Redis client instance (created once per process)."""
    global _pool, _client
    if _client is None:
        settings = get_settings()
        target_url = _resolve_redis_url(settings.REDIS_URL)
        _pool = ConnectionPool.from_url(
            target_url,
            decode_responses=True,
            max_connections=20,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
        _client = Redis(connection_pool=_pool)
    return _client


async def verify_redis_connection() -> bool:
    """Ping Redis to verify connectivity.

    Raises
    ------
    InfrastructureError
        If Redis is unreachable.
    """
    try:
        client = get_redis_client()
        pong = await client.ping()
        if not pong:
            raise InfrastructureError("Redis ping returned False.")
        logger.info("Redis connection verified successfully.")
        return True
    except InfrastructureError:
        raise
    except (RedisError, Exception) as exc:
        raise InfrastructureError(f"Failed to connect to Redis: {exc}") from exc


async def close_redis_client() -> None:
    """Close the global Redis client and connection pool."""
    global _pool, _client
    if _client is not None:
        await _client.close()
        _client = None
    if _pool is not None:
        await _pool.disconnect()
        _pool = None
    logger.info("Redis client connection pool closed.")


def _is_production() -> bool:
    """Return True when the process is configured for the production environment."""
    try:
        settings = get_settings()
        return settings.is_production
    except Exception:
        return False


# --------------------------------------------------------------------------- #
# Refresh Token JTI Revocation Tracking                                       #
# --------------------------------------------------------------------------- #


async def store_refresh_jti(jti: str, user_id: str, expire_seconds: int) -> None:
    """Persist a refresh token JTI in Redis with a TTL equal to the token lifetime.

    Production: propagates ``InfrastructureError`` on failure.
    Development/staging: logs a warning and continues.
    """
    try:
        client = get_redis_client()
        key = f"auth:refresh_token:{jti}"
        await client.set(key, user_id, ex=expire_seconds)
    except (RedisError, Exception) as exc:
        if _is_production():
            raise InfrastructureError(f"Failed to store refresh JTI: {exc}") from exc
        logger.warning("Redis unavailable — refresh JTI not persisted: %s", exc)


async def is_jti_revoked(jti: str) -> bool:
    """Return True when the JTI is absent from Redis or explicitly marked revoked.

    Production: propagates ``InfrastructureError`` on Redis failure (fail-closed).
    Development/staging: logs a warning and returns False (fail-open so logins work).
    """
    try:
        client = get_redis_client()
        key = f"auth:refresh_token:{jti}"
        value = await client.get(key)
        return value is None or value == "revoked"
    except (RedisError, Exception) as exc:
        if _is_production():
            # In production, treat a Redis failure as a revoked token (fail-closed).
            raise InfrastructureError(
                f"Failed to verify JTI revocation: {exc}"
            ) from exc
        logger.warning("Redis unavailable — JTI revocation check skipped: %s", exc)
        return False  # fail-open in dev/staging


async def revoke_jti(jti: str) -> None:
    """Delete a refresh token JTI from Redis (marks it as consumed).

    Production: propagates ``InfrastructureError`` on failure.
    Development/staging: logs a warning and continues.
    """
    try:
        client = get_redis_client()
        key = f"auth:refresh_token:{jti}"
        await client.delete(key)
    except (RedisError, Exception) as exc:
        if _is_production():
            raise InfrastructureError(f"Failed to revoke JTI: {exc}") from exc
        logger.warning("Redis unavailable — JTI revocation skipped: %s", exc)


# --------------------------------------------------------------------------- #
# Sliding Window Rate Limiter                                                 #
# --------------------------------------------------------------------------- #


async def check_rate_limit(
    key: str, limit: int, window_seconds: int
) -> tuple[bool, int]:
    """Evaluate a sliding-window rate limit for the given key.

    Returns
    -------
    tuple[bool, int]
        ``(is_allowed, remaining_requests)``

    Production: raises ``InfrastructureError`` when Redis is unreachable.
    Development/staging: logs a warning and fails open (allows the request).
    """
    try:
        client = get_redis_client()
        now = time.time()
        clear_before = now - window_seconds
        redis_key = f"ratelimit:{key}"

        async with client.pipeline(transaction=True) as pipe:
            pipe.zremrangebyscore(redis_key, 0, clear_before)
            pipe.zadd(redis_key, {str(now): now})
            pipe.zcard(redis_key)
            pipe.expire(redis_key, window_seconds)
            results: list[Any] = await pipe.execute()

        count: int = results[2]
        return count <= limit, max(0, limit - count)
    except (RedisError, Exception) as exc:
        if _is_production():
            raise InfrastructureError(f"Rate limiter Redis failure: {exc}") from exc
        logger.warning(
            "Redis unavailable — rate limiting disabled for this request: %s", exc
        )
        return True, limit
