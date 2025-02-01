import functools
import json
import logging
import pickle
from collections.abc import Awaitable
from typing import Callable, ParamSpec, TypeVar

import redis.asyncio as redis
from redis.typing import ExpiryT, ResponseT

from neuron_server.config import config

T = TypeVar("T")
P = ParamSpec("P")

logger = logging.getLogger(__name__)

client = redis.Redis(
    host=config.redis.host,
    port=config.redis.port,
    db=config.redis.db,
)


async def set_cache_key(
    key: str,
    value: bytes | str | int | float | bool | dict | list,
    ttl: ExpiryT | None = None,
) -> None:
    """Set a value in the Redis cache with optional TTL.

    Args:
        key: Cache key to set
        value: Value to store (must be serializable)
        ttl: Optional time-to-live in seconds
    """
    await client.set(key, pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL), ex=ttl)


async def get_cache_key(
    key: str,
) -> bytes | str | int | float | bool | dict | list | None:
    """Get a value from the Redis cache.

    Args:
        key: Cache key to retrieve

    Returns:
        The cached value if found and valid, None otherwise
    """
    cached_result: ResponseT | None = await client.get(key)
    if cached_result is not None:
        return pickle.loads(cached_result)
    return None


def cache_response(
    ttl: ExpiryT,
) -> Callable[[Callable[P, Awaitable[T]]], Callable[P, Awaitable[T]]]:
    """Decorator factory for caching async function responses in Redis.

    Args:
        ttl: Time-to-live for cached responses in seconds

    Returns:
        Decorator function that caches responses
    """

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # Generate cache key from function name and arguments
            cache_key_parts = [
                "cache_response",
                func.__name__,
                json.dumps(args),
                json.dumps(kwargs),
            ]
            key = ":".join(cache_key_parts)

            cached_result: ResponseT = await client.get(key)

            if cached_result is not None:
                try:
                    logger.debug("cache_response:hit=%s", key)
                    return pickle.loads(cached_result)
                except Exception as e:
                    logger.warning("Error unpickling cached result: %s", e)
                    await client.delete(key)

            result = await func(*args, **kwargs)
            await client.set(
                key, pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL), ex=ttl
            )
            return result

        return wrapper

    return decorator
