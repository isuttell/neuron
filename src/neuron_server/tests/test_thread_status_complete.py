"""Complete tests for thread status management."""

from datetime import datetime
from uuid import uuid4

import pytest

from neuron_server.llms.agent_status_manager import (
    AgentStatusManager,
    StatusEvent,
)


class TestStatusEvent:
    """Test StatusEvent dataclass."""

    def test_status_event_creation(self) -> None:
        """Test creating a StatusEvent."""
        timestamp = datetime.now()
        event = StatusEvent(
            timestamp=timestamp,
            event_type="start",
            operation="thinking",
            description="Processing your request",
        )

        assert event.timestamp == timestamp
        assert event.event_type == "start"
        assert event.operation == "thinking"
        assert event.description == "Processing your request"


class TestAgentStatusManager:
    """Test AgentStatusManager functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.manager = AgentStatusManager()
        self.test_thread_id = uuid4()

    def test_init(self) -> None:
        """Test AgentStatusManager initialization."""
        assert isinstance(self.manager._status_events, dict)
        assert isinstance(self.manager._status_agents, dict)
        assert isinstance(self.manager._thread_personalities, dict)
        assert isinstance(self.manager._cancelled_threads, set)

    def test_set_personality_info(self) -> None:
        """Test setting personality info for a thread."""
        name = "Test Assistant"
        context = "You are a helpful assistant"

        self.manager.set_personality_info(self.test_thread_id, name, context)

        assert self.test_thread_id in self.manager._thread_personalities
        assert self.manager._thread_personalities[self.test_thread_id] == (
            name,
            context,
        )

    def test_cancellation_tracking(self) -> None:
        """Test cancellation tracking functionality."""
        # Initially not cancelled
        assert not self.manager.is_cancelled(self.test_thread_id)

        # Mark as cancelled
        self.manager.mark_cancelled(self.test_thread_id)
        assert self.manager.is_cancelled(self.test_thread_id)

        # Unmark cancelled
        self.manager.unmark_cancelled(self.test_thread_id)
        assert not self.manager.is_cancelled(self.test_thread_id)

    @pytest.mark.asyncio
    async def test_add_tool_end_event(self) -> None:
        """Test adding tool end events."""
        # Initialize events list
        self.manager._status_events[self.test_thread_id] = []

        await self.manager.add_tool_end_event(self.test_thread_id, "web_search")

        events = self.manager._status_events[self.test_thread_id]
        assert len(events) == 1
        assert events[0].event_type == "end"
        assert events[0].operation == "web_search"
        assert "Searching the web" in events[0].description

    @pytest.mark.asyncio
    async def test_add_tool_end_event_unknown_tool(self) -> None:
        """Test adding end event for unknown tool."""
        self.manager._status_events[self.test_thread_id] = []

        await self.manager.add_tool_end_event(self.test_thread_id, "unknown_tool")

        events = self.manager._status_events[self.test_thread_id]
        assert len(events) == 1
        assert "Running unknown_tool" in events[0].description

    @pytest.mark.asyncio
    async def test_cleanup_thread(self) -> None:
        """Test thread cleanup functionality."""
        # Set up test data
        self.manager._status_events[self.test_thread_id] = []
        self.manager.set_personality_info(self.test_thread_id, "Test", "Context")

        # Create a mock agent
        class MockAgent:
            def __init__(self) -> None:
                self.reset_called = False

            def reset(self):
                self.reset_called = True

        mock_agent = MockAgent()
        self.manager._status_agents[self.test_thread_id] = mock_agent

        await self.manager.cleanup_thread(self.test_thread_id)

        # Verify cleanup
        assert mock_agent.reset_called
        assert self.test_thread_id not in self.manager._status_agents
        assert self.test_thread_id not in self.manager._status_events
        assert self.test_thread_id not in self.manager._thread_personalities

    def test_tool_descriptions_coverage(self) -> None:
        """Test that key tool descriptions are present."""
        descriptions = AgentStatusManager.TOOL_DESCRIPTIONS

        # Test key descriptions
        assert "web_search" in descriptions
        assert "thinking" in descriptions
        assert "streaming" in descriptions
        assert descriptions["web_search"] == "Searching the web"
        assert descriptions["thinking"] == "Processing your request"
        assert descriptions["streaming"] == "Writing response"


class TestGlobalFunctions:
    """Test global convenience functions."""

    def test_agent_status_manager_creation(self) -> None:
        """Test that AgentStatusManager creates independent instances."""
        manager1 = AgentStatusManager()
        manager2 = AgentStatusManager()

        assert isinstance(manager1, AgentStatusManager)
        assert isinstance(manager2, AgentStatusManager)
        # No longer a singleton - each instance is independent
        assert manager1 is not manager2


class TestToolDescriptions:
    """Test tool description mappings."""

    def test_memory_tools(self) -> None:
        """Test memory tool descriptions."""
        descriptions = AgentStatusManager.TOOL_DESCRIPTIONS

        assert "recall_memory" in descriptions
        assert "store_memory" in descriptions
        assert descriptions["recall_memory"] == "Retrieving conversation context"
        assert descriptions["store_memory"] == "Saving conversation context"

    def test_image_tools(self) -> None:
        """Test image tool descriptions."""
        descriptions = AgentStatusManager.TOOL_DESCRIPTIONS

        assert "replicate_image_generation" in descriptions
        assert "openai_image_generation" in descriptions
        assert (
            descriptions["replicate_image_generation"] == "Creating AI-generated image"
        )
        assert descriptions["openai_image_generation"] == "Creating image with DALL-E"

    def test_search_tools(self) -> None:
        """Test search tool descriptions."""
        descriptions = AgentStatusManager.TOOL_DESCRIPTIONS

        assert "web_search" in descriptions
        assert "arxiv_search" in descriptions
        assert descriptions["web_search"] == "Searching the web"
        assert descriptions["arxiv_search"] == "Searching academic papers"


class TestStatusCallbacks:
    """Test status callback functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.manager = AgentStatusManager()
        self.test_thread_id = uuid4()

    @pytest.mark.asyncio
    async def test_register_status_callback(self) -> None:
        """Test registering a status callback."""
        callback_calls = []

        async def test_callback(
            thread_id, raw_status, generated_message, human_message
        ):
            callback_calls.append(
                (thread_id, raw_status, generated_message, human_message)
            )

        self.manager.register_status_callback(self.test_thread_id, test_callback)

        # Verify callback is registered
        assert self.test_thread_id in self.manager._status_callbacks
        assert len(self.manager._status_callbacks[self.test_thread_id]) == 1
        assert self.manager._status_callbacks[self.test_thread_id][0] is test_callback

    @pytest.mark.asyncio
    async def test_register_multiple_callbacks(self) -> None:
        """Test registering multiple callbacks for same thread."""
        callback1_calls = []
        callback2_calls = []

        async def callback1(thread_id, raw_status, generated_message, human_message):
            callback1_calls.append("callback1")

        async def callback2(thread_id, raw_status, generated_message, human_message):
            callback2_calls.append("callback2")

        self.manager.register_status_callback(self.test_thread_id, callback1)
        self.manager.register_status_callback(self.test_thread_id, callback2)

        # Verify both callbacks are registered
        assert len(self.manager._status_callbacks[self.test_thread_id]) == 2

    @pytest.mark.asyncio
    async def test_unregister_specific_callback(self) -> None:
        """Test unregistering a specific callback."""

        async def callback1(thread_id, raw_status, generated_message, human_message):
            pass

        async def callback2(thread_id, raw_status, generated_message, human_message):
            pass

        # Register both callbacks
        self.manager.register_status_callback(self.test_thread_id, callback1)
        self.manager.register_status_callback(self.test_thread_id, callback2)

        # Unregister specific callback
        self.manager.unregister_status_callback(self.test_thread_id, callback1)

        # Only callback2 should remain
        assert len(self.manager._status_callbacks[self.test_thread_id]) == 1
        assert self.manager._status_callbacks[self.test_thread_id][0] is callback2

    @pytest.mark.asyncio
    async def test_unregister_all_callbacks(self) -> None:
        """Test unregistering all callbacks for a thread."""

        async def callback1(thread_id, raw_status, generated_message, human_message):
            pass

        async def callback2(thread_id, raw_status, generated_message, human_message):
            pass

        # Register both callbacks
        self.manager.register_status_callback(self.test_thread_id, callback1)
        self.manager.register_status_callback(self.test_thread_id, callback2)

        # Unregister all callbacks
        self.manager.unregister_status_callback(self.test_thread_id)

        # Thread should not be in callbacks dict anymore
        assert self.test_thread_id not in self.manager._status_callbacks

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_callback(self) -> None:
        """Test unregistering a callback that doesn't exist."""

        async def callback1(thread_id, raw_status, generated_message, human_message):
            pass

        async def callback2(thread_id, raw_status, generated_message, human_message):
            pass

        # Register only callback1
        self.manager.register_status_callback(self.test_thread_id, callback1)

        # Try to unregister callback2 (not registered) - should not raise error
        self.manager.unregister_status_callback(self.test_thread_id, callback2)

        # callback1 should still be there
        assert len(self.manager._status_callbacks[self.test_thread_id]) == 1
        assert self.manager._status_callbacks[self.test_thread_id][0] is callback1

    @pytest.mark.asyncio
    async def test_callback_invocation_during_status_update(self) -> None:
        """Test that callbacks are invoked during status updates."""
        from unittest.mock import AsyncMock, MagicMock, patch

        callback_calls = []

        async def test_callback(
            thread_id, raw_status, generated_message, human_message
        ):
            callback_calls.append(
                (thread_id, raw_status, generated_message, human_message)
            )

        self.manager.register_status_callback(self.test_thread_id, test_callback)

        # Mock dependencies for update_thread_status
        mock_thread = MagicMock()
        mock_thread.id = self.test_thread_id
        mock_thread.status = "idle"

        with patch(
            "neuron_server.llms.agent_status_manager.ThreadModel"
        ) as mock_thread_model:
            mock_thread_model.set = AsyncMock()

            with patch(
                "neuron_server.llms.agent_status_manager.StatusAgent"
            ) as mock_status_agent_class:
                mock_status_agent = AsyncMock()
                mock_status_agent.update_status = AsyncMock(
                    return_value=("Generated status", True)
                )
                mock_status_agent.last_execution_time = datetime.min
                mock_status_agent_class.return_value = mock_status_agent

                await self.manager.update_thread_status(
                    mock_thread, "thinking", human_message="Hello", callbacks=None
                )

                # Verify callback was called during update_status
                # The callback should be invoked by the nested status_callback function
                # We need to verify the mock was called with a callback function
                mock_status_agent.update_status.assert_called_once()
                call_args = mock_status_agent.update_status.call_args[0]
                assert (
                    len(call_args) == 4
                )  # status, recent_events, human_message, status_callback

                # The last argument should be the callback function
                status_callback_func = call_args[3]
                assert callable(status_callback_func)

                # Test the callback function
                await status_callback_func(
                    self.test_thread_id, "thinking", "Generated status", "Hello"
                )

                # Verify our test callback was invoked
                assert len(callback_calls) == 1
                assert callback_calls[0] == (
                    self.test_thread_id,
                    "thinking",
                    "Generated status",
                    "Hello",
                )

    @pytest.mark.asyncio
    async def test_callback_error_handling(self) -> None:
        """Test error handling when callbacks throw exceptions."""
        from unittest.mock import AsyncMock, MagicMock, patch

        successful_calls = []

        async def failing_callback(
            thread_id, raw_status, generated_message, human_message
        ):
            raise ValueError("Callback failed!")

        async def successful_callback(
            thread_id, raw_status, generated_message, human_message
        ):
            successful_calls.append("success")

        # Register both callbacks
        self.manager.register_status_callback(self.test_thread_id, failing_callback)
        self.manager.register_status_callback(self.test_thread_id, successful_callback)

        mock_thread = MagicMock()
        mock_thread.id = self.test_thread_id
        mock_thread.status = "idle"

        with patch(
            "neuron_server.llms.agent_status_manager.ThreadModel"
        ) as mock_thread_model:
            mock_thread_model.set = AsyncMock()

            with patch(
                "neuron_server.llms.agent_status_manager.StatusAgent"
            ) as mock_status_agent_class:
                mock_status_agent = AsyncMock()
                mock_status_agent.update_status = AsyncMock(
                    return_value=("Generated status", True)
                )
                mock_status_agent.last_execution_time = datetime.min
                mock_status_agent_class.return_value = mock_status_agent

                with patch(
                    "neuron_server.llms.agent_status_manager.logger"
                ) as mock_logger:
                    await self.manager.update_thread_status(
                        mock_thread, "thinking", human_message="Hello", callbacks=None
                    )

                    # Get the callback function from the mock call
                    call_args = mock_status_agent.update_status.call_args[0]
                    status_callback_func = call_args[3]

                    # Test the callback function
                    await status_callback_func(
                        self.test_thread_id, "thinking", "Generated status", "Hello"
                    )

                    # Verify error was logged
                    mock_logger.error.assert_called_once()
                    error_call = mock_logger.error.call_args[0][0]
                    assert "Error in status callback" in error_call

                    # Verify successful callback still ran
                    assert len(successful_calls) == 1

    @pytest.mark.asyncio
    async def test_cleanup_removes_callbacks(self) -> None:
        """Test that thread cleanup removes callbacks."""

        async def test_callback(
            thread_id, raw_status, generated_message, human_message
        ):
            pass

        # Register callback and set up other thread data
        self.manager.register_status_callback(self.test_thread_id, test_callback)
        self.manager._status_events[self.test_thread_id] = []
        self.manager.set_personality_info(self.test_thread_id, "Test", "Context")

        # Mock agent for cleanup
        class MockAgent:
            def reset(self):
                pass

        self.manager._status_agents[self.test_thread_id] = MockAgent()

        # Perform cleanup
        await self.manager.cleanup_thread(self.test_thread_id)

        # Verify callbacks were removed
        assert self.test_thread_id not in self.manager._status_callbacks


if __name__ == "__main__":
    pytest.main(["-v", __file__])
