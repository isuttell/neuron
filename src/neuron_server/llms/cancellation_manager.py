"""Cancellation management functionality."""

import asyncio
import contextlib
import json
from uuid import UUID

import redis.asyncio as redis

from neuron_server.config import config
from neuron_server.logger import logger


class CancellationManager:
    """Manages cancellation requests and listeners for agent threads."""

    def __init__(self) -> None:
        """Initialize the cancellation manager."""
        pass

    async def listen_for_cancellation(
        self, thread_id: UUID, cancel_event: asyncio.Event
    ) -> None:
        """Listen for cancellation requests for a specific thread.

        Args:
            thread_id: The thread ID to listen for cancellation
            cancel_event: Event to set when cancellation is requested
        """
        redis_client = redis.Redis(
            host=config.redis.host,
            port=config.redis.port,
            db=config.redis.db,
        )

        try:
            pubsub_client = redis_client.pubsub()
            await pubsub_client.subscribe("app")

            async for message in pubsub_client.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        if data.get("type") == "cancel_request" and data.get(
                            "thread_id"
                        ) == str(thread_id):
                            logger.debug(
                                f"Cancellation requested for thread {thread_id}"
                            )
                            cancel_event.set()
                            break
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception as e:
            logger.error(f"Error in cancellation listener: {e}")
        finally:
            await redis_client.aclose()

    async def handle_cancellation(
        self, stream_task: asyncio.Task, cancel_task: asyncio.Task, thread_id: UUID
    ) -> tuple[bool, any]:
        """Handle the result of cancellation monitoring.

        Args:
            stream_task: The main stream processing task
            cancel_task: The cancellation listening task
            thread_id: The thread ID being processed

        Returns:
            Tuple of (was_cancelled, result)
        """
        # Wait for either stream completion or cancellation
        done, pending = await asyncio.wait(
            [stream_task, cancel_task], return_when=asyncio.FIRST_COMPLETED
        )

        if cancel_task in done:
            # Cancellation was requested - cancel the stream task immediately
            logger.info(f"Cancelling stream task for thread {thread_id}")
            stream_task.cancel()
            return True, None
        # Stream completed normally - get the result
        result = stream_task.result() if stream_task.done() else None
        cancel_task.cancel()
        return False, result

    async def cleanup_pending_tasks(self, pending_tasks: set[asyncio.Task]) -> None:
        """Clean up any pending tasks after cancellation or completion.

        Args:
            pending_tasks: Set of pending tasks to cancel and await
        """
        for task in pending_tasks:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


# Global instance for convenience
_manager = CancellationManager()


async def listen_for_cancellation(thread_id: UUID, cancel_event: asyncio.Event) -> None:
    """Listen for cancellation requests for a specific thread."""
    await _manager.listen_for_cancellation(thread_id, cancel_event)


def get_cancellation_manager() -> CancellationManager:
    """Get the global cancellation manager instance."""
    return _manager
