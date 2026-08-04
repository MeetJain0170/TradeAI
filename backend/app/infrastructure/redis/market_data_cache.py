"""Redis caching helper for market data quotes, history, indices, and options chains."""

from __future__ import annotations

from redis.asyncio import RedisError

from app.core.exceptions import InfrastructureError
from app.infrastructure.logging.logger import get_logger
from app.infrastructure.redis.client import _is_production, get_redis_client

logger = get_logger(__name__)


async def get_market_data_cache(key: str) -> str | None:
    """Retrieve a cached market data JSON string from Redis by key.

    Returns
    -------
    str | None
        JSON payload string if cached hit, None if cache miss or error in dev.
    """
    try:
        client = get_redis_client()
        result = await client.get(key)
        if result is None:
            return None
        return result.decode("utf-8") if isinstance(result, bytes) else str(result)
    except (RedisError, Exception) as exc:
        if _is_production():
            raise InfrastructureError(
                f"Redis cache read error for key {key}: {exc}"
            ) from exc
        logger.warning(
            "Redis unavailable — market data cache read bypassed for key %s: %s",
            key,
            exc,
        )
        return None


async def set_market_data_cache(key: str, json_value: str, ttl_seconds: int) -> None:
    """Store a market data JSON string in Redis with a specified TTL."""
    try:
        client = get_redis_client()
        await client.set(key, json_value, ex=ttl_seconds)
    except (RedisError, Exception) as exc:
        if _is_production():
            raise InfrastructureError(
                f"Redis cache write error for key {key}: {exc}"
            ) from exc
        logger.warning(
            "Redis unavailable — market data cache write skipped for key %s: %s",
            key,
            exc,
        )
