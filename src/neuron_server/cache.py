import redis.asyncio as redis
from redis.typing import ExpiryT, ResponseT
from neuron_server.config import config
import functools
import json
from typing import Any
from neuron_server.logger import logger
import pickle

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
                try:
                    logger.debug(f"cache_response:hit={key}")
                    return pickle.loads(cached_result)
                except Exception as e:
                    logger.warning(f"Error unpickling cached result: {str(e)}")
                    await client.delete(key)

            result = await func(*args, **kwargs)
            await client.set(
                key, pickle.dumps(result, protocol=pickle.HIGHEST_PROTOCOL), ex=ttl
            )
            return result

        return wrapped

    return cache_response
