import redis.asyncio as redis
from redis.typing import ExpiryT, ResponseT
from neuron_server.config import config
import functools
import json
from typing import Any
from neuron_server.logger import logger

client = redis.Redis(
    host=config.redis.host,
    port=config.redis.port,
    db=config.redis.db,
)


def cache_response(ttl: ExpiryT):
    def cache_response(func):
        @functools.wraps(func)
        async def wrapped(*args, **kwargs):
            key = f"cache_response:{func.__name__}:{json.dumps(args)}:{json.dumps(kwargs)}"
            cached_result: ResponseT = await client.get(key)

            if cached_result is not None:
                logger.debug(f"cache_response:hit={key}")
                return cached_result.decode("utf-8")

            result: str = await func(*args, **kwargs)
            assert isinstance(result, str)
            await client.set(key, result, ex=ttl)
            return result

        return wrapped

    return cache_response
