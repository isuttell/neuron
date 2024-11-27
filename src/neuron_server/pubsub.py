import redis.asyncio as redis
from neuron_server.config import config
from pydantic import BaseModel

client = redis.Redis(
    host=config.redis.host,
    port=config.redis.port,
    db=config.redis.db,
)


class PubSub:
    def __init__(self):
        self.client = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
        )

    async def publish(self, channel: str, model: BaseModel):
        await self.client.publish(channel, model.model_dump_json())


pubsub = PubSub()
