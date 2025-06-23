"""Simplified tests for agent components that focus on core functionality."""

import asyncio
from uuid import uuid4

import pytest

from neuron_server.llms.agent_orchestrator import create_agent_orchestrator
from neuron_server.llms.cancellation_manager import get_cancellation_manager
from neuron_server.llms.message_processor import get_message_content
from neuron_server.llms.stream_event_processor import create_stream_event_processor
from neuron_server.llms.thread_status_manager import get_status_manager


class TestFactoryFunctions:
    """Test factory functions work correctly."""

    def test_create_agent_orchestrator(self) -> None:
        """Test agent orchestrator factory."""
        orchestrator = create_agent_orchestrator()
        assert orchestrator is not None
        assert orchestrator.status_manager is not None
        assert orchestrator.stream_processor is not None
        assert orchestrator.cancellation_manager is not None

    def test_get_status_manager(self) -> None:
        """Test status manager singleton."""
        manager1 = get_status_manager()
        manager2 = get_status_manager()
        assert manager1 is manager2

    def test_get_cancellation_manager(self) -> None:
        """Test cancellation manager singleton."""
        manager1 = get_cancellation_manager()
        manager2 = get_cancellation_manager()
        assert manager1 is manager2

    def test_create_stream_event_processor(self) -> None:
        """Test stream processor factory."""
        status_manager = get_status_manager()
        processor = create_stream_event_processor(status_manager)
        assert processor is not None
        assert processor.status_manager is status_manager


class TestMessageProcessor:
    """Test message content processing."""

    def test_get_message_content_string(self) -> None:
        """Test processing string content."""

        class MockMessage:
            def __init__(self, content) -> None:
                self.content = content

        message = MockMessage("Hello world")
        result = get_message_content(message, format_as_string=True)
        assert result == "Hello world"

    def test_get_message_content_structured(self) -> None:
        """Test processing structured content."""

        class MockMessage:
            def __init__(self, content) -> None:
                self.content = content

        message = MockMessage("Hello world")
        result = get_message_content(message, format_as_string=False)
        assert result == [{"type": "text", "text": "Hello world", "index": 0}]

    def test_get_message_content_none(self) -> None:
        """Test processing None content."""

        class MockMessage:
            def __init__(self, content) -> None:
                self.content = content

        message = MockMessage(None)
        result = get_message_content(message)
        assert result is None


class TestStatusManagerBasics:
    """Test basic status manager functionality."""

    def test_status_manager_init(self) -> None:
        """Test status manager initializes correctly."""
        manager = get_status_manager()
        assert hasattr(manager, "_status_events")
        assert hasattr(manager, "_status_agents")
        assert hasattr(manager, "_thread_personalities")
        assert hasattr(manager, "_cancelled_threads")

    def test_personality_info_management(self) -> None:
        """Test personality info management."""
        manager = get_status_manager()
        thread_id = uuid4()

        manager.set_personality_info(thread_id, "Test", "Context")
        assert thread_id in manager._thread_personalities
        assert manager._thread_personalities[thread_id] == ("Test", "Context")

    def test_cancellation_tracking(self) -> None:
        """Test cancellation tracking."""
        manager = get_status_manager()
        thread_id = uuid4()

        assert not manager.is_cancelled(thread_id)
        manager.mark_cancelled(thread_id)
        assert manager.is_cancelled(thread_id)
        manager.unmark_cancelled(thread_id)
        assert not manager.is_cancelled(thread_id)


class TestCancellationManagerBasics:
    """Test basic cancellation manager functionality."""

    def test_cancellation_manager_init(self) -> None:
        """Test cancellation manager initializes."""
        manager = get_cancellation_manager()
        assert manager is not None

    @pytest.mark.asyncio
    async def test_cleanup_pending_tasks(self) -> None:
        """Test cleanup of pending tasks."""
        manager = get_cancellation_manager()

        async def dummy_task():
            await asyncio.sleep(1)

        task1 = asyncio.create_task(dummy_task())
        task2 = asyncio.create_task(dummy_task())

        await manager.cleanup_pending_tasks({task1, task2})

        assert task1.cancelled()
        assert task2.cancelled()


class TestStreamEventProcessorBasics:
    """Test basic stream event processor functionality."""

    def test_clean_run_id(self) -> None:
        """Test run ID cleaning functionality."""
        status_manager = get_status_manager()
        processor = create_stream_event_processor(status_manager)

        # Test cleaning run IDs
        assert processor._clean_run_id("run-abc123") == "abc123"
        assert processor._clean_run_id("run--def456") == "def456"
        assert processor._clean_run_id("abc123") == "abc123"

    def test_processor_has_status_manager(self) -> None:
        """Test processor is connected to status manager."""
        status_manager = get_status_manager()
        processor = create_stream_event_processor(status_manager)
        assert processor.status_manager is status_manager


class TestComponentIntegration:
    """Test that components work together."""

    def test_orchestrator_has_all_components(self) -> None:
        """Test orchestrator has all required components."""
        orchestrator = create_agent_orchestrator()

        # Should have all three main components
        assert orchestrator.status_manager is not None
        assert orchestrator.stream_processor is not None
        assert orchestrator.cancellation_manager is not None

        # Stream processor should use the same status manager
        assert (
            orchestrator.stream_processor.status_manager is orchestrator.status_manager
        )

    def test_singleton_consistency(self) -> None:
        """Test that singletons are consistent across the system."""
        orchestrator = create_agent_orchestrator()

        # Should use singleton instances
        assert orchestrator.status_manager is get_status_manager()
        assert orchestrator.cancellation_manager is get_cancellation_manager()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
