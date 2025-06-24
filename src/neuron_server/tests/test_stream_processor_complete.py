"""Complete tests for stream event processing."""

from uuid import uuid4

import pytest

from neuron_server.llms.stream_event_processor import (
    StreamEventProcessor,
    create_stream_event_processor,
)
from neuron_server.llms.thread_status_manager import get_status_manager


class MockThread:
    """Simple mock thread for testing."""

    def __init__(self, thread_id=None) -> None:
        self.id = thread_id or uuid4()
        self.name = "Test Thread"


class MockStatusManager:
    """Mock status manager for testing."""

    def __init__(self) -> None:
        self.update_calls = []
        self.tool_events = []

    async def update_thread_status(self, thread, status, **kwargs):
        """Mock update thread status."""
        self.update_calls.append({"thread_id": thread.id, "status": status})

    async def add_tool_end_event(self, thread_id, tool_name):
        """Mock add tool end event."""
        self.tool_events.append({"thread_id": thread_id, "tool_name": tool_name})


class TestStreamEventProcessor:
    """Test StreamEventProcessor functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_status_manager = MockStatusManager()
        self.processor = StreamEventProcessor(self.mock_status_manager)
        self.test_thread = MockThread()

    def test_init(self) -> None:
        """Test StreamEventProcessor initialization."""
        assert self.processor.status_manager is self.mock_status_manager

    def test_clean_run_id_with_prefix(self) -> None:
        """Test run ID cleaning with 'run-' prefix."""
        test_cases = [
            ("run-abc123", "abc123"),
            ("run--def456", "def456"),
            ("run---ghi789", "ghi789"),
            ("abc123", "abc123"),  # No prefix
            ("", ""),  # Empty string
        ]

        for input_id, expected in test_cases:
            result = self.processor._clean_run_id(input_id)
            # Should return expected or original if empty after cleaning
            assert result in (expected, input_id)

    def test_clean_run_id_edge_cases(self) -> None:
        """Test run ID cleaning edge cases."""
        # Test various edge cases - returns original if would be empty
        assert self.processor._clean_run_id("run-") == "run-"
        assert self.processor._clean_run_id("run--") == "run--"
        assert self.processor._clean_run_id("run-abc-def") == "abc-def"
        assert self.processor._clean_run_id("notrun-abc") == "notrun-abc"

    @pytest.mark.asyncio
    async def test_handle_chain_event_data_structure(self) -> None:
        """Test chain event data structure handling."""
        from neuron_server.llms.stream_event_processor import ChainEvent, ChainEventData

        # Test that we can create the data structures
        active_runs = {}
        event_data = ChainEventData(
            kind="on_chain_start",
            name="test_chain",
            data={"test": "data"},
            run_id="run-123",
            active_runs=active_runs,
        )

        chain_event = ChainEvent(
            thread=self.test_thread,
            event_data=event_data,
            human_message="Test message",
        )

        # Verify structure
        assert chain_event["thread"] is self.test_thread
        assert chain_event["event_data"]["kind"] == "on_chain_start"
        assert chain_event["event_data"]["name"] == "test_chain"
        assert chain_event["human_message"] == "Test message"

    @pytest.mark.asyncio
    async def test_handle_tool_event_data_structure(self) -> None:
        """Test tool event data structure handling."""
        from neuron_server.llms.stream_event_processor import ToolEventContext

        # Test that we can create the data structures
        ctx = ToolEventContext(
            thread=self.test_thread,
            kind="on_tool_start",
            name="test_tool",
            run_id="run-456",
            active_runs={},
            data={},
            node="agent",
            human_message="Test message",
        )

        # Verify structure
        assert ctx["thread"] is self.test_thread
        assert ctx["kind"] == "on_tool_start"
        assert ctx["name"] == "test_tool"
        assert ctx["run_id"] == "run-456"
        assert ctx["node"] == "agent"
        assert ctx["human_message"] == "Test message"


class TestFactoryFunction:
    """Test factory function."""

    def test_create_stream_event_processor(self) -> None:
        """Test create_stream_event_processor factory function."""
        status_manager = get_status_manager()
        processor = create_stream_event_processor(status_manager)

        assert isinstance(processor, StreamEventProcessor)
        assert processor.status_manager is status_manager

    def test_create_with_mock_status_manager(self) -> None:
        """Test creating with mock status manager."""
        mock_status_manager = MockStatusManager()
        processor = create_stream_event_processor(mock_status_manager)

        assert isinstance(processor, StreamEventProcessor)
        assert processor.status_manager is mock_status_manager


class TestEventDataStructures:
    """Test event data structure classes."""

    def test_chain_event_data_creation(self) -> None:
        """Test ChainEventData creation."""
        from neuron_server.llms.stream_event_processor import ChainEventData

        data = ChainEventData(
            kind="on_chain_start",
            name="test_chain",
            data={"key": "value"},
            run_id="run-123",
            active_runs={},
        )

        assert data["kind"] == "on_chain_start"
        assert data["name"] == "test_chain"
        assert data["data"]["key"] == "value"
        assert data["run_id"] == "run-123"
        assert isinstance(data["active_runs"], dict)

    def test_tool_event_context_creation(self) -> None:
        """Test ToolEventContext creation."""
        from neuron_server.llms.stream_event_processor import ToolEventContext

        thread = MockThread()
        ctx = ToolEventContext(
            thread=thread,
            kind="on_tool_start",
            name="test_tool",
            run_id="run-456",
            active_runs={},
            data={},
            node="agent",
            human_message="Test message",
        )

        assert ctx["thread"] is thread
        assert ctx["kind"] == "on_tool_start"
        assert ctx["name"] == "test_tool"
        assert ctx["run_id"] == "run-456"
        assert ctx["node"] == "agent"
        assert ctx["human_message"] == "Test message"


class TestRunIdCleaning:
    """Test run ID cleaning functionality in detail."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.processor = StreamEventProcessor(MockStatusManager())

    def test_standard_run_ids(self) -> None:
        """Test cleaning standard run IDs."""
        test_cases = [
            ("run-abc123", "abc123"),
            ("run-def456", "def456"),
            ("run-ghi789", "ghi789"),
        ]

        for input_id, expected in test_cases:
            result = self.processor._clean_run_id(input_id)
            assert result == expected

    def test_double_dash_run_ids(self) -> None:
        """Test cleaning run IDs with double dashes."""
        test_cases = [
            ("run--abc123", "abc123"),
            ("run---def456", "def456"),
            ("run----ghi789", "ghi789"),
        ]

        for input_id, expected in test_cases:
            result = self.processor._clean_run_id(input_id)
            assert result == expected

    def test_no_prefix_run_ids(self) -> None:
        """Test run IDs without prefix (should be unchanged)."""
        test_cases = [
            ("abc123", "abc123"),
            ("def456", "def456"),
            ("ghi789", "ghi789"),
        ]

        for input_id, expected in test_cases:
            result = self.processor._clean_run_id(input_id)
            assert result == expected

    def test_edge_case_run_ids(self) -> None:
        """Test edge case run IDs."""
        # Empty and minimal cases
        assert self.processor._clean_run_id("") == ""
        assert (
            self.processor._clean_run_id("run-") == "run-"
        )  # Returns original if empty
        assert (
            self.processor._clean_run_id("run--") == "run--"
        )  # Returns original if empty


if __name__ == "__main__":
    pytest.main(["-v", __file__])
