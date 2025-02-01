import redis.asyncio as redis
from pydantic import BaseModel

from neuron_server.config import config

client = redis.Redis(
    host=config.redis.host,
    port=config.redis.port,
    db=config.redis.db,
)


class PubSub:
    def __init__(self) -> None:
        self.client = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
        )

    async def publish(self, channel: str, model: BaseModel) -> None:
        await self.client.publish(channel, model.model_dump_json())


pubsub = PubSub()
