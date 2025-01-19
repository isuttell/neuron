from neuron_server.util.scheduler import AsyncRedisEventScheduler
from typing import Dict, Any
import asyncio
import logging

from neuron_server.models.thread_model import ThreadModel
from neuron_server.models.stream_event import StreamEvent

logger = logging.getLogger(__name__)


class TaskScheduler(AsyncRedisEventScheduler):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 2,
        password: str = None,
    ):
        super().__init__(host=host, port=port, db=db, password=password)

    async def on_event(self, event_id: str, metadata: Dict[str, Any]):
        from neuron_server.llms.agent import astream

        logger.debug(f"Stream event triggered: {event_id}")
        body = StreamEvent(**metadata)

        thread = (
            await ThreadModel.create(
                personality_id=body.personality_id,
                user_id=body.user_id,
            )
            if body.thread_id is None
            else await ThreadModel.get(body.thread_id)
        )

        if not thread:
            logger.error(f"Thread not found: {body.thread_id}")
            return

        asyncio.create_task(
            astream(
                thread_id=thread.id,
                personality_id=body.personality_id,
                user_id=body.user_id,
                username=body.username,
                prompt=f"<|AI|>{body.prompt}<|AI|>",
            )
        )
