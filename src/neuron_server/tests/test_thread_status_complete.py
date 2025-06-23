"""Complete tests for thread status management."""

from datetime import datetime
from uuid import uuid4

import pytest

from neuron_server.llms.thread_status_manager import (
    StatusEvent,
    ThreadStatusManager,
    get_status_manager,
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


class TestThreadStatusManager:
    """Test ThreadStatusManager functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.manager = ThreadStatusManager()
        self.test_thread_id = uuid4()

    def test_init(self) -> None:
        """Test ThreadStatusManager initialization."""
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
        descriptions = ThreadStatusManager.TOOL_DESCRIPTIONS

        # Test key descriptions
        assert "web_search" in descriptions
        assert "thinking" in descriptions
        assert "streaming" in descriptions
        assert descriptions["web_search"] == "Searching the web"
        assert descriptions["thinking"] == "Processing your request"
        assert descriptions["streaming"] == "Writing response"


class TestGlobalFunctions:
    """Test global convenience functions."""

    def test_get_status_manager_singleton(self) -> None:
        """Test that get_status_manager returns singleton."""
        manager1 = get_status_manager()
        manager2 = get_status_manager()

        assert isinstance(manager1, ThreadStatusManager)
        assert manager1 is manager2


class TestToolDescriptions:
    """Test tool description mappings."""

    def test_memory_tools(self) -> None:
        """Test memory tool descriptions."""
        descriptions = ThreadStatusManager.TOOL_DESCRIPTIONS

        assert "recall_memory" in descriptions
        assert "store_memory" in descriptions
        assert descriptions["recall_memory"] == "Retrieving conversation context"
        assert descriptions["store_memory"] == "Saving conversation context"

    def test_image_tools(self) -> None:
        """Test image tool descriptions."""
        descriptions = ThreadStatusManager.TOOL_DESCRIPTIONS

        assert "replicate_image_generation" in descriptions
        assert "openai_image_generation" in descriptions
        assert (
            descriptions["replicate_image_generation"] == "Creating AI-generated image"
        )
        assert descriptions["openai_image_generation"] == "Creating image with DALL-E"

    def test_search_tools(self) -> None:
        """Test search tool descriptions."""
        descriptions = ThreadStatusManager.TOOL_DESCRIPTIONS

        assert "web_search" in descriptions
        assert "arxiv_search" in descriptions
        assert descriptions["web_search"] == "Searching the web"
        assert descriptions["arxiv_search"] == "Searching academic papers"


if __name__ == "__main__":
    pytest.main(["-v", __file__])
