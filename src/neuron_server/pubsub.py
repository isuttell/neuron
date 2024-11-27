import redis.asyncio as redis
from neuron_server.config import config


client = redis.Redis(
    host=config.redis.host,
    port=config.redis.port,
    db=config.redis.db,
)
