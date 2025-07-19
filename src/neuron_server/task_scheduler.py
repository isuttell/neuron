import asyncio
import logging
from datetime import datetime
from typing import Any

from neuron_server.models.stream_event import StreamEvent
from neuron_server.models.thread_model import ThreadModel
from neuron_server.util.scheduler import (
    AbstractAsyncRedisEventScheduler,
    RecurringPattern,
)

logger = logging.getLogger(__name__)


class TaskScheduler(AbstractAsyncRedisEventScheduler):
    def __init__(
        self,
        host: str = "localhost",
        port: int = 6379,
        db: int = 2,
        password: str | None = None,
    ) -> None:
        super().__init__(host=host, port=port, db=db, password=password)
        self._active_streams: dict[str, asyncio.Task] = {}

    async def update_event(
        self,
        event_id: str,
        event_data: dict[str, Any],
        trigger_time: datetime | None = None,
        recurring_pattern: RecurringPattern | None = None,
    ) -> None:
        """Update an existing scheduled event with new parameters."""
        logger.debug(f"Updating event {event_id}")

        # Get existing event to preserve any unmodified fields
        existing_event = await self.get_event(event_id)
        if not existing_event:
            raise ValueError(f"Event {event_id} not found")

        # Schedule new event with updated parameters
        await self.schedule_event(
            event_id=event_id,
            event_data=event_data,
            trigger_time=trigger_time,
            recurring_pattern=recurring_pattern,
        )

    async def on_event(self, event_id: str, metadata: dict[str, Any]) -> None:
        """Handle scheduled events."""
        # Handle session cleanup events
        if metadata.get("task_type") == "session_cleanup":
            await self._handle_session_cleanup()
            return

        # Handle stream events by creating a new thread and streaming response
        from neuron_server.llms.agent import astream

        try:
            # Format timestamp for logging
            timestamp = datetime.now(self.timezone).isoformat()
            logger.info(f"Processing stream event {event_id} at {timestamp} UTC")

            # Parse event data
            body = StreamEvent(**metadata)

            # Create or get thread
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

            # Cancel any existing stream for this thread
            if thread.id in self._active_streams:
                logger.debug(f"Cancelling existing stream for thread {thread.id}")
                self._active_streams[thread.id].cancel()

            # Define a wrapper to safely run the stream task
            async def run_stream() -> None:
                try:
                    await astream(
                        {
                            "thread_id": thread.id,
                            "personality_id": body.personality_id,
                            "user_id": body.user_id,
                            "username": body.username,
                            "prompt": f"<|AI|>{body.prompt}<|AI|>",
                        }
                    )
                except Exception as stream_error:
                    logger.error(
                        f"Stream error for thread {thread.id}: {stream_error}",
                        exc_info=True,
                    )

            # Start new stream with error handling
            stream_task = asyncio.create_task(run_stream())

            # Track active stream
            self._active_streams[thread.id] = stream_task

            # Clean up when stream completes
            stream_task.add_done_callback(
                lambda _: self._active_streams.pop(thread.id, None)
            )

        except Exception as e:
            logger.error(f"Error processing event {event_id}: {str(e)}", exc_info=True)
            # Do not propagate the exception so that recurring events are rescheduled
            return

    async def _handle_session_cleanup(self) -> None:
        """Handle session cleanup task."""
        try:
            from neuron_server.websocket_session_manager import session_manager

            timestamp = datetime.now(self.timezone).isoformat()
            logger.debug(f"Running session cleanup at {timestamp} UTC")

            cleanup_count = await session_manager.cleanup_sessions()

            if cleanup_count > 0:
                logger.info(
                    f"Session cleanup completed: {cleanup_count} sessions cleaned"
                )
            else:
                logger.debug("Session cleanup completed: no sessions to clean")

        except Exception as e:
            logger.error(f"Error during session cleanup: {str(e)}", exc_info=True)

    async def schedule_session_cleanup(self, interval_hours: int = 1) -> None:
        """Schedule recurring session cleanup task.

        Args:
            interval_hours: How often to run cleanup (default: 1 hour)
        """
        pattern = RecurringPattern(interval=interval_hours, unit="hours")

        await self.schedule_event(
            event_id="session_cleanup",
            event_data={"task_type": "session_cleanup", "user_id": "system"},
            recurring_pattern=pattern,
        )

        logger.info(f"Session cleanup scheduled to run every {interval_hours} hour(s)")
