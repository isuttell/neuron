"""Tests for task_scheduler module."""

import asyncio
import contextlib
from collections.abc import AsyncIterator
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from neuron_server.models.stream_event import StreamEvent
from neuron_server.task_scheduler import TaskScheduler
from neuron_server.util.scheduler import RecurringPattern


@pytest.fixture
def mock_redis_connection() -> Mock:
    """Mock Redis connection."""
    with patch("neuron_server.util.scheduler.redis.asyncio.Redis") as mock_redis:
        yield mock_redis


@pytest.fixture
async def task_scheduler(mock_redis_connection: Mock) -> AsyncIterator[TaskScheduler]:
    """Create a TaskScheduler instance with mocked Redis."""
    scheduler = TaskScheduler(host="localhost", port=6379, db=2, password="test")
    scheduler.redis = mock_redis_connection
    yield scheduler
    # Cleanup
    if hasattr(scheduler, "_active_streams"):
        # Create a copy to avoid "dictionary changed size during iteration"
        tasks = list(scheduler._active_streams.values())
        for task in tasks:
            if isinstance(task, asyncio.Task) and not task.done():
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task


@pytest.fixture
def sample_stream_event() -> StreamEvent:
    """Create a sample StreamEvent."""
    return StreamEvent(
        thread_id="test-thread-123",
        personality_id="test-personality",
        user_id="test-user",
        username="testuser",
        prompt="Test prompt for scheduled event",
    )


class TestTaskScheduler:
    """Test cases for TaskScheduler class."""

    @pytest.mark.asyncio
    async def test_init(self) -> None:
        """Test TaskScheduler initialization."""
        scheduler = TaskScheduler(host="test-host", port=1234, db=5, password="secret")
        assert scheduler._active_streams == {}
        # Parent class stores connection info internally
        assert isinstance(scheduler, TaskScheduler)

    @pytest.mark.asyncio
    async def test_update_event_success(self, task_scheduler: TaskScheduler) -> None:
        """Test successful event update."""
        event_id = "test-event-123"
        existing_event = {
            "event_id": event_id,
            "event_data": {"old": "data"},
            "trigger_time": datetime.now(timezone.utc),
        }
        new_event_data = {"new": "data"}
        new_trigger_time = datetime.now(timezone.utc) + timedelta(hours=1)

        # Mock get_event to return existing event
        task_scheduler.get_event = AsyncMock(return_value=existing_event)
        task_scheduler.schedule_event = AsyncMock()

        await task_scheduler.update_event(
            event_id=event_id,
            event_data=new_event_data,
            trigger_time=new_trigger_time,
        )

        # Verify get_event was called
        task_scheduler.get_event.assert_called_once_with(event_id)

        # Verify schedule_event was called with new data
        task_scheduler.schedule_event.assert_called_once_with(
            event_id=event_id,
            event_data=new_event_data,
            trigger_time=new_trigger_time,
            recurring_pattern=None,
        )

    @pytest.mark.asyncio
    async def test_update_event_not_found(self, task_scheduler: TaskScheduler) -> None:
        """Test updating non-existent event raises ValueError."""
        event_id = "non-existent-event"

        # Mock get_event to return None
        task_scheduler.get_event = AsyncMock(return_value=None)

        with pytest.raises(ValueError, match=f"Event {event_id} not found"):
            await task_scheduler.update_event(
                event_id=event_id, event_data={"test": "data"}
            )

    @pytest.mark.asyncio
    async def test_update_event_with_recurring_pattern(
        self, task_scheduler: TaskScheduler
    ) -> None:
        """Test updating event with recurring pattern."""
        event_id = "recurring-event"
        existing_event = {"event_id": event_id, "event_data": {"old": "data"}}
        recurring_pattern = RecurringPattern(interval=1, unit="days")

        task_scheduler.get_event = AsyncMock(return_value=existing_event)
        task_scheduler.schedule_event = AsyncMock()

        await task_scheduler.update_event(
            event_id=event_id,
            event_data={"new": "data"},
            recurring_pattern=recurring_pattern,
        )

        # Verify recurring pattern was passed
        task_scheduler.schedule_event.assert_called_once()
        call_args = task_scheduler.schedule_event.call_args[1]
        assert call_args["recurring_pattern"] == recurring_pattern

    @pytest.mark.asyncio
    @patch("neuron_server.task_scheduler.ThreadModel")
    async def test_on_event_with_existing_thread(
        self,
        mock_thread_model: Mock,
        task_scheduler: TaskScheduler,
        sample_stream_event: StreamEvent,
    ) -> None:
        """Test processing event with existing thread."""
        event_id = "test-event"
        metadata = sample_stream_event.model_dump()

        # Mock thread retrieval
        mock_thread = Mock(id="test-thread-123")
        mock_thread_model.get = AsyncMock(return_value=mock_thread)

        # Mock astream at the source module with a delay to keep task alive
        async def delayed_astream(*args: Any, **kwargs: Any) -> None:
            await asyncio.sleep(0.2)  # Keep task alive long enough for checks

        with patch("neuron_server.llms.agent.astream", new=delayed_astream):
            await task_scheduler.on_event(event_id, metadata)

            # Verify thread was retrieved
            mock_thread_model.get.assert_called_once_with("test-thread-123")

            # Give the async task time to start
            await asyncio.sleep(0.05)

            # Verify stream task was tracked
            assert "test-thread-123" in task_scheduler._active_streams

            # Wait for task to complete
            await asyncio.sleep(0.2)

    @pytest.mark.asyncio
    @patch("neuron_server.task_scheduler.ThreadModel")
    async def test_on_event_create_new_thread(
        self,
        mock_thread_model: Mock,
        task_scheduler: TaskScheduler,
    ) -> None:
        """Test processing event that creates a new thread."""
        event_id = "test-event"
        # Create a stream event with no thread
        sample_event = StreamEvent(
            thread_id="",  # Empty string to simulate no thread
            personality_id="test-personality",
            user_id="test-user",
            username="testuser",
            prompt="Test prompt for new thread",
        )

        # Modify event data to have None thread_id after validation
        metadata = sample_event.model_dump()
        metadata["thread_id"] = None

        # Mock thread creation
        mock_thread = Mock(id="new-thread-456")
        mock_thread_model.create = AsyncMock(return_value=mock_thread)

        # Mock astream at the source module
        with (
            patch(
                "neuron_server.llms.agent.astream", new_callable=AsyncMock
            ) as mock_astream,
            patch("neuron_server.task_scheduler.StreamEvent") as mock_stream_event,
        ):
            # Make it return our modified data
            mock_stream_event.return_value = sample_event
            mock_stream_event.return_value.thread_id = None

            await task_scheduler.on_event(event_id, metadata)

            # Verify thread was created
            mock_thread_model.create.assert_called_once_with(
                personality_id="test-personality", user_id="test-user"
            )

            # Wait a bit for async task
            await asyncio.sleep(0.1)

            # Verify astream was called with the new thread
            mock_astream.assert_called_once_with(
                {
                    "thread_id": "new-thread-456",
                    "personality_id": "test-personality",
                    "user_id": "test-user",
                    "username": "testuser",
                    "prompt": "<|AI|>Test prompt for new thread<|AI|>",
                }
            )

    @pytest.mark.asyncio
    @patch("neuron_server.task_scheduler.ThreadModel")
    async def test_on_event_thread_not_found(
        self,
        mock_thread_model: Mock,
        task_scheduler: TaskScheduler,
        sample_stream_event: StreamEvent,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test processing event when thread is not found."""
        event_id = "test-event"
        metadata = sample_stream_event.model_dump()

        # Mock thread retrieval to return None
        mock_thread_model.get = AsyncMock(return_value=None)

        await task_scheduler.on_event(event_id, metadata)

        # Verify error was logged
        assert "Thread not found: test-thread-123" in caplog.text

    @pytest.mark.asyncio
    @patch("neuron_server.task_scheduler.ThreadModel")
    async def test_on_event_cancel_existing_stream(
        self,
        mock_thread_model: Mock,
        task_scheduler: TaskScheduler,
        sample_stream_event: StreamEvent,
    ) -> None:
        """Test that existing stream is cancelled when new event arrives."""
        event_id = "test-event"
        metadata = sample_stream_event.model_dump()
        thread_id = "test-thread-123"

        # Mock thread
        mock_thread = Mock(id=thread_id)
        mock_thread_model.get = AsyncMock(return_value=mock_thread)

        # Create a mock existing stream task
        existing_task = Mock(spec=asyncio.Task)
        existing_task.cancel = Mock()
        existing_task.done = Mock(return_value=False)
        task_scheduler._active_streams[thread_id] = existing_task

        # Mock astream at the source module
        with patch("neuron_server.llms.agent.astream", new_callable=AsyncMock):
            await task_scheduler.on_event(event_id, metadata)

            # Verify existing task was cancelled
            existing_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    @patch("neuron_server.task_scheduler.ThreadModel")
    async def test_on_event_stream_error(
        self,
        mock_thread_model: Mock,
        task_scheduler: TaskScheduler,
        sample_stream_event: StreamEvent,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test handling of stream errors."""
        event_id = "test-event"
        metadata = sample_stream_event.model_dump()

        # Mock thread
        mock_thread = Mock(id="test-thread-123")
        mock_thread_model.get = AsyncMock(return_value=mock_thread)

        # Mock astream at the source module to raise an error
        with patch(
            "neuron_server.llms.agent.astream",
            new_callable=AsyncMock,
            side_effect=Exception("Stream processing failed"),
        ):
            await task_scheduler.on_event(event_id, metadata)

            # Wait for async task to complete
            await asyncio.sleep(0.1)

            # Verify error was logged
            assert "Stream error for thread test-thread-123" in caplog.text
            assert "Stream processing failed" in caplog.text

    @pytest.mark.asyncio
    async def test_on_event_invalid_metadata(
        self, task_scheduler: TaskScheduler, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test handling of invalid event metadata."""
        event_id = "test-event"
        invalid_metadata = {"invalid": "data"}  # Missing required fields

        await task_scheduler.on_event(event_id, invalid_metadata)

        # Verify error was logged
        assert f"Error processing event {event_id}" in caplog.text

    @pytest.mark.asyncio
    @patch("neuron_server.task_scheduler.ThreadModel")
    async def test_on_event_cleanup_completed_stream(
        self,
        mock_thread_model: Mock,
        task_scheduler: TaskScheduler,
        sample_stream_event: StreamEvent,
    ) -> None:
        """Test that completed streams are cleaned up from active streams."""
        event_id = "test-event"
        metadata = sample_stream_event.model_dump()
        thread_id = "test-thread-123"

        # Mock thread
        mock_thread = Mock(id=thread_id)
        mock_thread_model.get = AsyncMock(return_value=mock_thread)

        # Mock astream to complete quickly
        async def quick_stream(*args: Any, **kwargs: Any) -> None:
            await asyncio.sleep(0.01)

        with patch("neuron_server.llms.agent.astream", new=quick_stream):
            await task_scheduler.on_event(event_id, metadata)

            # Verify stream task was added
            assert thread_id in task_scheduler._active_streams

            # Wait for stream to complete and cleanup
            await asyncio.sleep(0.1)

            # Verify stream was cleaned up
            assert thread_id not in task_scheduler._active_streams

    @pytest.mark.asyncio
    @patch("neuron_server.task_scheduler.datetime")
    async def test_on_event_logging_timestamp(
        self,
        mock_datetime: Mock,
        task_scheduler: TaskScheduler,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that event processing logs include timestamp."""
        # Mock datetime
        mock_now = Mock()
        mock_now.isoformat.return_value = "2024-01-15T10:30:00+00:00"
        mock_datetime.now.return_value = mock_now

        event_id = "test-event"
        # Invalid metadata to trigger early return
        metadata = {"invalid": "data"}

        with caplog.at_level("INFO"):
            await task_scheduler.on_event(event_id, metadata)

        # Verify timestamp was included in log
        assert f"Processing stream event {event_id} at" in caplog.text

    @pytest.mark.asyncio
    @patch("neuron_server.task_scheduler.logger")
    async def test_update_event_debug_logging(
        self, mock_logger: Mock, task_scheduler: TaskScheduler
    ) -> None:
        """Test debug logging in update_event."""
        event_id = "test-event"
        task_scheduler.get_event = AsyncMock(return_value={"event_id": event_id})
        task_scheduler.schedule_event = AsyncMock()

        await task_scheduler.update_event(event_id, {"test": "data"})

        mock_logger.debug.assert_called_with(f"Updating event {event_id}")
