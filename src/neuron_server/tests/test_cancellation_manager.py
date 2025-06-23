"""Tests for cancellation management functionality."""

import asyncio
import contextlib
import json
from collections.abc import AsyncIterator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from neuron_server.llms.cancellation_manager import (
    CancellationManager,
    get_cancellation_manager,
    listen_for_cancellation,
)


class MockRedisClient:
    """Mock Redis client for testing."""

    def __init__(self) -> None:
        self.pubsub_messages: list[dict[str, Any]] = []
        self.closed = False

    def pubsub(self) -> "MockPubsub":
        """Return mock pubsub client."""
        return MockPubsub(self.pubsub_messages)

    async def aclose(self) -> None:
        """Mock close method."""
        self.closed = True


class MockPubsub:
    """Mock Redis pubsub client for testing."""

    def __init__(self, messages: list[dict[str, Any]]) -> None:
        self.messages = messages
        self.subscribed_channels: list[str] = []

    async def subscribe(self, channel: str) -> None:
        """Mock subscribe method."""
        self.subscribed_channels.append(channel)

    async def listen(self) -> AsyncIterator[dict[str, Any]]:
        """Mock listen method that yields test messages."""
        # Yield initial subscription confirmation
        yield {"type": "subscribe", "channel": b"app", "data": 1}

        # Yield test messages
        for message in self.messages:
            yield message


class TestCancellationManager:
    """Test cases for CancellationManager class."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.manager = CancellationManager()
        self.test_thread_id = uuid4()

    @pytest.mark.asyncio
    async def test_listen_for_cancellation_valid_request(self) -> None:
        """Test listening for valid cancellation request."""
        cancel_event = asyncio.Event()

        # Create mock Redis client with cancellation message
        mock_redis = MockRedisClient()
        mock_redis.pubsub_messages = [
            {
                "type": "message",
                "data": json.dumps(
                    {"type": "cancel_request", "thread_id": str(self.test_thread_id)}
                ),
            }
        ]

        with patch(
            "neuron_server.llms.cancellation_manager.redis.Redis",
            return_value=mock_redis,
        ):
            # Start listening task
            listen_task = asyncio.create_task(
                self.manager.listen_for_cancellation(self.test_thread_id, cancel_event)
            )

            # Wait a bit for the task to process the message
            await asyncio.sleep(0.1)

            # Verify the cancel event was set
            assert cancel_event.is_set()

            # Clean up
            listen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await listen_task

    @pytest.mark.asyncio
    async def test_listen_for_cancellation_wrong_thread_id(self) -> None:
        """Test that cancellation requests for other threads are ignored."""
        cancel_event = asyncio.Event()
        other_thread_id = uuid4()

        # Create mock Redis client with cancellation for different thread
        mock_redis = MockRedisClient()
        mock_redis.pubsub_messages = [
            {
                "type": "message",
                "data": json.dumps(
                    {"type": "cancel_request", "thread_id": str(other_thread_id)}
                ),
            }
        ]

        with patch(
            "neuron_server.llms.cancellation_manager.redis.Redis",
            return_value=mock_redis,
        ):
            # Start listening task
            listen_task = asyncio.create_task(
                self.manager.listen_for_cancellation(self.test_thread_id, cancel_event)
            )

            # Wait a bit for the task to process the message
            await asyncio.sleep(0.1)

            # Verify the cancel event was NOT set
            assert not cancel_event.is_set()

            # Clean up
            listen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await listen_task

    @pytest.mark.asyncio
    async def test_listen_for_cancellation_invalid_json(self) -> None:
        """Test handling of invalid JSON messages."""
        cancel_event = asyncio.Event()

        # Create mock Redis client with invalid JSON
        mock_redis = MockRedisClient()
        mock_redis.pubsub_messages = [
            {"type": "message", "data": "invalid json"},
            {
                "type": "message",
                "data": json.dumps(
                    {"type": "cancel_request", "thread_id": str(self.test_thread_id)}
                ),
            },
        ]

        with patch(
            "neuron_server.llms.cancellation_manager.redis.Redis",
            return_value=mock_redis,
        ):
            # Start listening task
            listen_task = asyncio.create_task(
                self.manager.listen_for_cancellation(self.test_thread_id, cancel_event)
            )

            # Wait a bit for the task to process messages
            await asyncio.sleep(0.1)

            # Should still receive valid cancellation after invalid message
            assert cancel_event.is_set()

            # Clean up
            listen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await listen_task

    @pytest.mark.asyncio
    async def test_listen_for_cancellation_wrong_message_type(self) -> None:
        """Test ignoring messages that aren't cancel_request type."""
        cancel_event = asyncio.Event()

        # Create mock Redis client with wrong message type
        mock_redis = MockRedisClient()
        mock_redis.pubsub_messages = [
            {
                "type": "message",
                "data": json.dumps(
                    {"type": "other_request", "thread_id": str(self.test_thread_id)}
                ),
            }
        ]

        with patch(
            "neuron_server.llms.cancellation_manager.redis.Redis",
            return_value=mock_redis,
        ):
            # Start listening task
            listen_task = asyncio.create_task(
                self.manager.listen_for_cancellation(self.test_thread_id, cancel_event)
            )

            # Wait a bit for the task to process the message
            await asyncio.sleep(0.1)

            # Verify the cancel event was NOT set
            assert not cancel_event.is_set()

            # Clean up
            listen_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await listen_task

    @pytest.mark.asyncio
    async def test_listen_for_cancellation_redis_error(self) -> None:
        """Test handling of Redis connection errors."""
        cancel_event = asyncio.Event()

        # Mock Redis to raise an exception
        with patch(
            "neuron_server.llms.cancellation_manager.redis.Redis"
        ) as mock_redis_class:
            mock_redis = AsyncMock()
            mock_redis.pubsub.side_effect = Exception("Redis connection error")
            mock_redis_class.return_value = mock_redis

            # This should not raise an exception, just log the error
            await self.manager.listen_for_cancellation(
                self.test_thread_id, cancel_event
            )

            # Verify Redis client close was called
            mock_redis.aclose.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_cancellation_stream_completed_first(self) -> None:
        """Test handling when stream task completes before cancellation."""
        # Create mock tasks
        stream_result = "Stream completed successfully"
        stream_task = MagicMock()
        stream_task.done.return_value = True
        stream_task.result.return_value = stream_result

        cancel_task = MagicMock()
        cancel_task.cancel = MagicMock()

        # Mock asyncio.wait to simulate stream completing first
        async def mock_wait(tasks, **kwargs):
            return {stream_task}, {cancel_task}

        with patch("asyncio.wait", mock_wait):
            was_cancelled, result = await self.manager.handle_cancellation(
                stream_task, cancel_task, self.test_thread_id
            )

            assert not was_cancelled
            assert result == stream_result
            cancel_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_cancellation_cancelled_first(self) -> None:
        """Test handling when cancellation occurs before stream completion."""
        # Create mock tasks
        stream_task = AsyncMock()
        cancel_task = AsyncMock()

        # Mock asyncio.wait to simulate cancellation first
        async def mock_wait(tasks, **kwargs):
            return {cancel_task}, {stream_task}

        with patch("asyncio.wait", mock_wait):
            was_cancelled, result = await self.manager.handle_cancellation(
                stream_task, cancel_task, self.test_thread_id
            )

            assert was_cancelled
            assert result is None
            stream_task.cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_pending_tasks(self) -> None:
        """Test cleanup of pending tasks."""

        # Create real async tasks
        async def dummy_task():
            await asyncio.sleep(10)

        task1 = asyncio.create_task(dummy_task())
        task2 = asyncio.create_task(dummy_task())
        pending_tasks = {task1, task2}

        await self.manager.cleanup_pending_tasks(pending_tasks)

        # Verify both tasks were cancelled
        assert task1.cancelled()
        assert task2.cancelled()

    @pytest.mark.asyncio
    async def test_cleanup_pending_tasks_with_cancellation_error(self) -> None:
        """Test cleanup handles CancelledError gracefully."""

        # Create mock task that raises CancelledError when awaited
        async def mock_cancelled_task():
            raise asyncio.CancelledError()

        task = asyncio.create_task(mock_cancelled_task())
        pending_tasks = {task}

        # This should not raise an exception
        await self.manager.cleanup_pending_tasks(pending_tasks)

        # Verify task was cancelled
        assert task.cancelled()


class TestGlobalFunctions:
    """Test cases for global convenience functions."""

    @pytest.mark.asyncio
    async def test_global_listen_for_cancellation(self) -> None:
        """Test global listen_for_cancellation function."""
        thread_id = uuid4()
        cancel_event = asyncio.Event()

        with patch.object(
            CancellationManager, "listen_for_cancellation", AsyncMock()
        ) as mock_listen:
            await listen_for_cancellation(thread_id, cancel_event)
            mock_listen.assert_called_once_with(thread_id, cancel_event)

    def test_get_cancellation_manager(self) -> None:
        """Test get_cancellation_manager returns CancellationManager instance."""
        manager = get_cancellation_manager()
        assert isinstance(manager, CancellationManager)

        # Should return the same instance (singleton behavior)
        manager2 = get_cancellation_manager()
        assert manager is manager2


class TestIntegrationScenarios:
    """Integration test scenarios for cancellation manager."""

    @pytest.mark.asyncio
    async def test_full_cancellation_flow(self) -> None:
        """Test complete cancellation flow from request to task cleanup."""
        thread_id = uuid4()
        manager = CancellationManager()

        # Create a long-running stream task
        async def long_running_stream():
            await asyncio.sleep(10)  # Long operation
            return "Stream result"

        # Create cancellation event and stream task
        cancel_event = asyncio.Event()
        stream_task = asyncio.create_task(long_running_stream())

        # Set up mock Redis with cancellation message
        mock_redis = MockRedisClient()
        mock_redis.pubsub_messages = [
            {
                "type": "message",
                "data": json.dumps(
                    {"type": "cancel_request", "thread_id": str(thread_id)}
                ),
            }
        ]

        with patch(
            "neuron_server.llms.cancellation_manager.redis.Redis",
            return_value=mock_redis,
        ):
            # Start cancellation listener
            cancel_task = asyncio.create_task(
                manager.listen_for_cancellation(thread_id, cancel_event)
            )

            # Wait a bit for cancellation to be detected
            await asyncio.sleep(0.1)

            # Handle cancellation
            was_cancelled, result = await manager.handle_cancellation(
                stream_task, cancel_task, thread_id
            )

            # Verify cancellation occurred
            assert was_cancelled
            assert result is None

            # Clean up - stream task should be cancelled by handle_cancellation
            await manager.cleanup_pending_tasks({cancel_task})

    @pytest.mark.asyncio
    async def test_multiple_threads_cancellation(self) -> None:
        """Test cancellation handling for multiple threads simultaneously."""
        thread_id_1 = uuid4()
        thread_id_2 = uuid4()
        manager = CancellationManager()

        cancel_event_1 = asyncio.Event()
        cancel_event_2 = asyncio.Event()

        # Set up mock Redis with cancellation for thread_1 only
        mock_redis = MockRedisClient()
        mock_redis.pubsub_messages = [
            {
                "type": "message",
                "data": json.dumps(
                    {"type": "cancel_request", "thread_id": str(thread_id_1)}
                ),
            }
        ]

        with patch(
            "neuron_server.llms.cancellation_manager.redis.Redis",
            return_value=mock_redis,
        ):
            # Start listeners for both threads
            listen_task_1 = asyncio.create_task(
                manager.listen_for_cancellation(thread_id_1, cancel_event_1)
            )
            listen_task_2 = asyncio.create_task(
                manager.listen_for_cancellation(thread_id_2, cancel_event_2)
            )

            # Wait for processing
            await asyncio.sleep(0.1)

            # Only thread_1 should be cancelled
            assert cancel_event_1.is_set()
            assert not cancel_event_2.is_set()

            # Clean up
            for task in [listen_task_1, listen_task_2]:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task


if __name__ == "__main__":
    pytest.main(["-v", __file__])
