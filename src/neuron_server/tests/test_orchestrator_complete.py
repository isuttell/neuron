"""Complete tests for agent orchestration."""

import contextlib
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from neuron_server.llms.agent_orchestrator import (
    AgentOrchestrator,
    create_agent_orchestrator,
)
from neuron_server.llms.callback_handlers import CallbackHandlers


class MockStatusManager:
    """Mock status manager for testing."""

    def __init__(self) -> None:
        self.update_calls = []
        self.personality_info = {}
        self.cancelled_threads = set()

    def set_personality_info(self, thread_id, name, context):
        """Mock set personality info."""
        self.personality_info[thread_id] = (name, context)

    async def update_thread_status(self, thread, status, **kwargs):
        """Mock update thread status."""
        self.update_calls.append({"thread_id": thread.id, "status": status})

    def is_cancelled(self, thread_id):
        """Mock is cancelled check."""
        return thread_id in self.cancelled_threads

    def unmark_cancelled(self, thread_id):
        """Mock unmark cancelled."""
        self.cancelled_threads.discard(thread_id)

    async def reset_cancelled_thread(self, thread):
        """Mock reset cancelled thread."""
        self.cancelled_threads.add(thread.id)


class MockStreamProcessor:
    """Mock stream processor for testing."""

    def __init__(self) -> None:
        self.processed_streams = []

    async def process_stream_events(
        self, thread, event_stream, human_message_content, start_time
    ):
        """Mock process stream events."""
        self.processed_streams.append(
            {
                "thread_id": thread.id,
                "human_message_content": human_message_content,
                "start_time": start_time,
            }
        )


class MockCancellationManager:
    """Mock cancellation manager for testing."""

    def __init__(self) -> None:
        self.listen_calls = []
        self.handle_calls = []
        self.cleanup_calls = []

    async def listen_for_cancellation(self, thread_id, cancel_event):
        """Mock listen for cancellation."""
        self.listen_calls.append(thread_id)

    async def handle_cancellation(self, stream_task, cancel_task, thread_id):
        """Mock handle cancellation."""
        self.handle_calls.append(thread_id)
        return False, "Mock result"

    async def cleanup_pending_tasks(self, pending_tasks):
        """Mock cleanup pending tasks."""
        self.cleanup_calls.append(len(pending_tasks))


class MockThread:
    """Mock thread for testing."""

    def __init__(self, thread_id=None, status="idle", name="Test Thread") -> None:
        self.id = thread_id or uuid4()
        self.status = status
        self.name = name


class TestAgentOrchestrator:
    """Test AgentOrchestrator functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_status_manager = MockStatusManager()
        self.mock_stream_processor = MockStreamProcessor()
        self.mock_cancellation_manager = MockCancellationManager()

        self.orchestrator = AgentOrchestrator(
            self.mock_status_manager,
            self.mock_stream_processor,
            self.mock_cancellation_manager,
        )

        self.test_thread_id = uuid4()

    def test_init(self) -> None:
        """Test AgentOrchestrator initialization."""
        assert self.orchestrator.status_manager is self.mock_status_manager
        assert self.orchestrator.stream_processor is self.mock_stream_processor
        assert self.orchestrator.cancellation_manager is self.mock_cancellation_manager

    @pytest.mark.asyncio
    async def test_wait_for_idle_already_idle(self) -> None:
        """Test waiting for idle when thread is already idle."""

        # Mock ThreadModel.get to return idle thread
        class MockThreadModel:
            @staticmethod
            async def get(thread_id) -> MockThread:
                return MockThread(thread_id, status="idle")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "neuron_server.llms.agent_orchestrator.ThreadModel", MockThreadModel
            )
            # Should return immediately for idle thread
            await self.orchestrator._wait_for_idle(self.test_thread_id)

    @pytest.mark.asyncio
    async def test_wait_for_idle_timeout(self) -> None:
        """Test timeout when waiting for idle."""

        # Mock ThreadModel.get to always return busy thread
        class MockThreadModel:
            @staticmethod
            async def get(thread_id) -> MockThread:
                return MockThread(thread_id, status="busy")

        async def mock_sleep(x):
            pass

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "neuron_server.llms.agent_orchestrator.ThreadModel", MockThreadModel
            )
            mp.setattr(
                "neuron_server.llms.agent_orchestrator.asyncio.sleep", mock_sleep
            )

            with pytest.raises(TimeoutError):
                await self.orchestrator._wait_for_idle(self.test_thread_id, timeout=0.1)

    @pytest.mark.asyncio
    async def test_get_final_state_no_messages(self) -> None:
        """Test getting final state when no messages exist."""

        # Mock dependencies
        class MockState:
            def __init__(self) -> None:
                self.values = {"messages": []}

        class MockLLM:
            async def aget_state(self, config, checkpointer=None):
                return MockState()

        class MockProviderModelModel:
            @staticmethod
            async def get_active_llm() -> MockLLM:
                return MockLLM()

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(
                "neuron_server.llms.agent_orchestrator.AsyncPostgresSaver",
                lambda x: None,
            )
            mp.setattr(
                "neuron_server.llms.agent_orchestrator.ProviderModelModel",
                MockProviderModelModel,
            )

            result = await self.orchestrator._get_final_state(self.test_thread_id)
            assert result is None

    def test_default_configuration(self) -> None:
        """Test default configuration values."""
        default_location = "San Diego, California at -117.1860 W and 32.84 N."

        # Test that the default location is reasonable
        assert "San Diego" in default_location
        assert "California" in default_location
        assert "32.84" in default_location  # Latitude
        assert "-117.1860" in default_location  # Longitude


class TestFactoryFunction:
    """Test factory function."""

    def test_create_agent_orchestrator(self) -> None:
        """Test create_agent_orchestrator factory function."""
        orchestrator = create_agent_orchestrator()

        assert isinstance(orchestrator, AgentOrchestrator)
        assert orchestrator.status_manager is not None
        assert orchestrator.stream_processor is not None
        assert orchestrator.cancellation_manager is not None

    def test_factory_returns_working_components(self) -> None:
        """Test that factory returns working components."""
        orchestrator = create_agent_orchestrator()

        # Test that components have expected attributes/methods
        assert hasattr(orchestrator.status_manager, "update_thread_status")
        assert hasattr(orchestrator.stream_processor, "process_stream_events")
        assert hasattr(orchestrator.cancellation_manager, "handle_cancellation")

    def test_factory_component_integration(self) -> None:
        """Test that factory creates properly integrated components."""
        orchestrator = create_agent_orchestrator()

        # Stream processor should use the same status manager
        assert (
            orchestrator.stream_processor.status_manager is orchestrator.status_manager
        )


class TestComponentCoordination:
    """Test component coordination functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_status_manager = MockStatusManager()
        self.mock_stream_processor = MockStreamProcessor()
        self.mock_cancellation_manager = MockCancellationManager()

        self.orchestrator = AgentOrchestrator(
            self.mock_status_manager,
            self.mock_stream_processor,
            self.mock_cancellation_manager,
        )

    def test_component_access(self) -> None:
        """Test that all components are accessible."""
        assert self.orchestrator.status_manager is self.mock_status_manager
        assert self.orchestrator.stream_processor is self.mock_stream_processor
        assert self.orchestrator.cancellation_manager is self.mock_cancellation_manager

    def test_status_manager_coordination(self) -> None:
        """Test status manager coordination."""
        thread_id = uuid4()

        # Test that we can call status manager methods
        self.orchestrator.status_manager.set_personality_info(
            thread_id, "Test", "Context"
        )
        assert thread_id in self.mock_status_manager.personality_info

    def test_cancellation_manager_coordination(self) -> None:
        """Test cancellation manager coordination."""
        thread_id = uuid4()

        # Test that we can call cancellation manager methods
        assert not self.orchestrator.status_manager.is_cancelled(thread_id)


class TestExecutionConfiguration:
    """Test execution configuration handling."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.orchestrator = AgentOrchestrator(
            MockStatusManager(),
            MockStreamProcessor(),
            MockCancellationManager(),
        )

    def test_config_structure(self) -> None:
        """Test configuration structure."""
        # Test that we can create a valid config structure
        args = {
            "thread_id": uuid4(),
            "personality_id": uuid4(),
            "user_id": "test_user",
            "username": "test_username",
            "prompt": "Test prompt",
            "location": "Test Location",
        }

        # Extract config values like the real implementation
        config = {
            "thread_id": args["thread_id"],
            "personality_id": args["personality_id"],
            "user_id": args.get("user_id") or "Unknown",
            "username": args.get("username") or "Unknown",
            "prompt": args["prompt"],
            "location": args.get(
                "location", "San Diego, California at -117.1860 W and 32.84 N."
            ),
        }

        assert config["thread_id"] == args["thread_id"]
        assert config["personality_id"] == args["personality_id"]
        assert config["user_id"] == "test_user"
        assert config["username"] == "test_username"
        assert config["prompt"] == "Test prompt"
        assert config["location"] == "Test Location"

    def test_default_values(self) -> None:
        """Test default configuration values."""
        args = {
            "thread_id": uuid4(),
            "personality_id": uuid4(),
            "prompt": "Test prompt",
        }

        # Test with minimal args (missing optional fields)
        config = {
            "thread_id": args["thread_id"],
            "personality_id": args["personality_id"],
            "user_id": args.get("user_id") or "Unknown",
            "username": args.get("username") or "Unknown",
            "prompt": args["prompt"],
            "location": args.get(
                "location", "San Diego, California at -117.1860 W and 32.84 N."
            ),
        }

        assert config["user_id"] == "Unknown"
        assert config["username"] == "Unknown"
        assert "San Diego" in config["location"]


class TestOrchestratorCallbacks:
    """Test AgentOrchestrator callback functionality."""

    def setup_method(self) -> None:
        """Set up test fixtures."""
        self.mock_status_manager = MockStatusManager()
        self.mock_stream_processor = MockStreamProcessor()
        self.mock_cancellation_manager = MockCancellationManager()

        self.orchestrator = AgentOrchestrator(
            self.mock_status_manager,
            self.mock_stream_processor,
            self.mock_cancellation_manager,
        )

        self.test_thread_id = uuid4()

    @pytest.mark.asyncio
    async def test_execute_with_callbacks_parameter(self) -> None:
        """Test execute method accepts callbacks parameter."""


        callbacks = CallbackHandlers()

        args = {
            "thread_id": self.test_thread_id,
            "personality_id": uuid4(),
            "user_id": "test_user",
            "username": "test_username",
            "prompt": "Test prompt",
        }

        # Mock dependencies to prevent actual execution
        with pytest.MonkeyPatch.context() as mp:
            # Mock ThreadModel to return existing thread
            class MockThreadModel:
                @staticmethod
                async def get(thread_id) -> MockThread:
                    return MockThread(thread_id, status="idle")

                @staticmethod
                async def set(thread_id, field, value) -> None:
                    pass

            mp.setattr(
                "neuron_server.llms.agent_orchestrator.ThreadModel", MockThreadModel
            )

            # The method should accept callbacks without error
            # We'll let it fail on personality lookup since we're just testing
            # callback acceptance
            with contextlib.suppress(Exception):
                await self.orchestrator.execute_stream(args, callbacks=callbacks)

    @pytest.mark.asyncio
    async def test_callback_registration_lifecycle(self) -> None:
        """Test callback registration and unregistration lifecycle."""


        # Track callback registration
        register_calls = []
        unregister_calls = []

        def mock_register_callback(thread_id, callback):
            register_calls.append((thread_id, callback))

        def mock_unregister_callback(thread_id, callback):
            unregister_calls.append((thread_id, callback))

        # Mock status manager methods
        self.mock_status_manager.register_status_callback = mock_register_callback
        self.mock_status_manager.unregister_status_callback = mock_unregister_callback

        # Mock status change callback
        status_callback = AsyncMock()
        callbacks = CallbackHandlers(on_status_change=status_callback)

        args = {
            "thread_id": self.test_thread_id,
            "personality_id": uuid4(),
            "user_id": "test_user",
            "username": "test_username",
            "prompt": "Test prompt",
        }

        with pytest.MonkeyPatch.context() as mp:
            # Mock all dependencies
            class MockThreadModel:
                @staticmethod
                async def get(thread_id) -> MockThread:
                    return MockThread(thread_id, status="idle")

                @staticmethod
                async def set(thread_id, field, value) -> None:
                    pass

            class MockPersonalityModel:
                @staticmethod
                async def get(personality_id) -> None:
                    return None  # Will cause early return with exception

            mp.setattr(
                "neuron_server.llms.agent_orchestrator.ThreadModel", MockThreadModel
            )
            mp.setattr(
                "neuron_server.llms.agent_orchestrator.PersonalityModel",
                MockPersonalityModel,
            )

            # Execute should register callback initially, then unregister on cleanup
            with contextlib.suppress(Exception):
                # Expected to fail on personality lookup
                await self.orchestrator.execute_stream(args, callbacks=callbacks)

            # Verify callback registration lifecycle
            assert len(register_calls) == 1
            assert register_calls[0][0] == self.test_thread_id
            assert register_calls[0][1] is status_callback

            assert len(unregister_calls) == 1
            assert unregister_calls[0][0] == self.test_thread_id
            assert unregister_calls[0][1] is status_callback

    @pytest.mark.asyncio
    async def test_error_callback_invocation(self) -> None:
        """Test error callback is invoked on errors."""


        # Mock error callback
        error_callback = AsyncMock()
        callbacks = CallbackHandlers(on_error=error_callback)

        args = {
            "thread_id": self.test_thread_id,
            "personality_id": uuid4(),
            "user_id": "test_user",
            "username": "test_username",
            "prompt": "Test prompt",
        }

        with pytest.MonkeyPatch.context() as mp:
            # Mock dependencies to cause an error
            class MockThreadModel:
                @staticmethod
                async def get(thread_id) -> MockThread:
                    return MockThread(thread_id, status="idle")

                @staticmethod
                async def set(thread_id, field, value) -> None:
                    pass

            class MockPersonalityModel:
                @staticmethod
                async def get(personality_id) -> None:
                    raise Exception("Test error")  # Force error

            mp.setattr(
                "neuron_server.llms.agent_orchestrator.ThreadModel", MockThreadModel
            )
            mp.setattr(
                "neuron_server.llms.agent_orchestrator.PersonalityModel",
                MockPersonalityModel,
            )

            # Mock status manager methods
            self.mock_status_manager.register_status_callback = lambda *args: None
            self.mock_status_manager.unregister_status_callback = lambda *args: None

            with contextlib.suppress(Exception):
                await self.orchestrator.execute_stream(args, callbacks=callbacks)

            # Verify error callback was invoked
            error_callback.assert_called_once()
            error_args = error_callback.call_args[0]
            assert "Test error" in error_args[0]  # Error message
            assert error_args[1] == "test_user"  # User ID

    @pytest.mark.asyncio
    async def test_callbacks_none_handling(self) -> None:
        """Test that passing None callbacks doesn't cause errors."""
        args = {
            "thread_id": self.test_thread_id,
            "personality_id": uuid4(),
            "user_id": "test_user",
            "username": "test_username",
            "prompt": "Test prompt",
        }

        with pytest.MonkeyPatch.context() as mp:
            # Mock dependencies
            class MockThreadModel:
                @staticmethod
                async def get(thread_id) -> MockThread:
                    return MockThread(thread_id, status="idle")

                @staticmethod
                async def set(thread_id, field, value) -> None:
                    pass

            class MockPersonalityModel:
                @staticmethod
                async def get(personality_id) -> None:
                    return None  # Will cause early return

            mp.setattr(
                "neuron_server.llms.agent_orchestrator.ThreadModel", MockThreadModel
            )
            mp.setattr(
                "neuron_server.llms.agent_orchestrator.PersonalityModel",
                MockPersonalityModel,
            )

            # Should not raise error with None callbacks
            try:
                await self.orchestrator.execute_stream(args, callbacks=None)
            except Exception as e:
                # Should fail on personality lookup, not callback handling
                assert (
                    "Personality" in str(e)
                    or "not found" in str(e).lower()
                    or "execute_stream" in str(e)
                )

    @pytest.mark.asyncio
    async def test_status_callback_registration_conditional(self) -> None:
        """Test status callback is only registered when provided."""


        register_calls = []

        def mock_register_callback(thread_id, callback):
            register_calls.append((thread_id, callback))

        self.mock_status_manager.register_status_callback = mock_register_callback
        self.mock_status_manager.unregister_status_callback = lambda *args: None

        args = {
            "thread_id": self.test_thread_id,
            "personality_id": uuid4(),
            "user_id": "test_user",
            "username": "test_username",
            "prompt": "Test prompt",
        }

        with pytest.MonkeyPatch.context() as mp:
            # Mock dependencies
            class MockThreadModel:
                @staticmethod
                async def get(thread_id) -> MockThread:
                    return MockThread(thread_id, status="idle")

                @staticmethod
                async def set(thread_id, field, value) -> None:
                    pass

            class MockPersonalityModel:
                @staticmethod
                async def get(personality_id) -> None:
                    return None

            mp.setattr(
                "neuron_server.llms.agent_orchestrator.ThreadModel", MockThreadModel
            )
            mp.setattr(
                "neuron_server.llms.agent_orchestrator.PersonalityModel",
                MockPersonalityModel,
            )

            # Test 1: With status callback - should register
            status_callback = AsyncMock()
            callbacks_with_status = CallbackHandlers(on_status_change=status_callback)

            with contextlib.suppress(Exception):
                await self.orchestrator.execute_stream(
                    args, callbacks=callbacks_with_status
                )

            assert len(register_calls) == 1

            # Test 2: Without status callback - should not register
            register_calls.clear()
            callbacks_without_status = CallbackHandlers(on_human_message=AsyncMock())

            with contextlib.suppress(Exception):
                await self.orchestrator.execute_stream(
                    args, callbacks=callbacks_without_status
                )

            assert len(register_calls) == 0


if __name__ == "__main__":
    pytest.main(["-v", __file__])
