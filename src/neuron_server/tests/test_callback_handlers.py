"""Tests for callback handlers."""

from datetime import datetime
from uuid import uuid4

import pytest

from neuron_server.controllers.events.message_events import (
    PartialMessage,
    ThreadMessage,
)
from neuron_server.llms.callback_handlers import CallbackHandlers
from neuron_server.models.thread_model import ThreadModel
from neuron_server.tools.artifact_types import ToolMediaArtifact, ToolMediaItem


class TestCallbackHandlers:
    """Test CallbackHandlers dataclass functionality."""

    def test_init_empty(self) -> None:
        """Test creating CallbackHandlers with no callbacks."""
        handlers = CallbackHandlers()

        assert handlers.on_status_change is None
        assert handlers.on_human_message is None
        assert handlers.on_ai_message is None
        assert handlers.on_tool_message is None
        assert handlers.on_stream_token is None
        assert handlers.on_thread_update is None
        assert handlers.on_error is None
        assert handlers.on_media_artifacts is None

    def test_init_with_callbacks(self) -> None:
        """Test creating CallbackHandlers with callbacks."""

        async def mock_status_callback(
            thread_id, raw_status, generated_message, human_message
        ):
            pass

        async def mock_message_callback(message):
            pass

        async def mock_partial_callback(partial_message):
            pass

        async def mock_thread_callback(thread):
            pass

        async def mock_error_callback(error_message, user_id):
            pass

        async def mock_media_callback(artifacts):
            pass

        handlers = CallbackHandlers(
            on_status_change=mock_status_callback,
            on_human_message=mock_message_callback,
            on_ai_message=mock_message_callback,
            on_tool_message=mock_message_callback,
            on_stream_token=mock_partial_callback,
            on_thread_update=mock_thread_callback,
            on_error=mock_error_callback,
            on_media_artifacts=mock_media_callback,
        )

        assert handlers.on_status_change is mock_status_callback
        assert handlers.on_human_message is mock_message_callback
        assert handlers.on_ai_message is mock_message_callback
        assert handlers.on_tool_message is mock_message_callback
        assert handlers.on_stream_token is mock_partial_callback
        assert handlers.on_thread_update is mock_thread_callback
        assert handlers.on_error is mock_error_callback
        assert handlers.on_media_artifacts is mock_media_callback

    def test_partial_initialization(self) -> None:
        """Test creating CallbackHandlers with only some callbacks."""

        async def mock_status_callback(
            thread_id, raw_status, generated_message, human_message
        ):
            pass

        async def mock_error_callback(error_message, user_id):
            pass

        handlers = CallbackHandlers(
            on_status_change=mock_status_callback,
            on_error=mock_error_callback,
        )

        assert handlers.on_status_change is mock_status_callback
        assert handlers.on_error is mock_error_callback
        # All others should be None
        assert handlers.on_human_message is None
        assert handlers.on_ai_message is None
        assert handlers.on_tool_message is None
        assert handlers.on_stream_token is None
        assert handlers.on_thread_update is None
        assert handlers.on_media_artifacts is None

    @pytest.mark.asyncio
    async def test_callback_signatures(self) -> None:
        """Test that callbacks have correct signatures."""
        # Mock data for testing
        thread_id = uuid4()
        mock_message = ThreadMessage(
            id=str(uuid4()),
            thread_id=thread_id,
            type="human",
            content="test message",
        )
        mock_partial = PartialMessage(
            id=str(uuid4()),
            thread_id=thread_id,
            type="ai",
            content="test",
            index=0,
            status="streaming",
            node="agent",
        )
        mock_thread = ThreadModel(
            id=thread_id,
            name="Test Thread",
            status="idle",
            personality_id=uuid4(),
            user_id="test_user",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        mock_artifacts = [
            ToolMediaArtifact(
                media_type="image",
                items=[
                    ToolMediaItem(
                        id=uuid4(),
                        url="test.jpg",
                        name="test image",
                        description="test image description",
                    )
                ],
            )
        ]

        # Track callback invocations
        invocations = []

        async def status_callback(
            thread_id, raw_status, generated_message, human_message
        ):
            invocations.append(
                ("status", thread_id, raw_status, generated_message, human_message)
            )

        async def message_callback(message):
            invocations.append(("message", message))

        async def partial_callback(partial_message):
            invocations.append(("partial", partial_message))

        async def thread_callback(thread):
            invocations.append(("thread", thread))

        async def error_callback(error_message, user_id):
            invocations.append(("error", error_message, user_id))

        async def media_callback(artifacts):
            invocations.append(("media", artifacts))

        handlers = CallbackHandlers(
            on_status_change=status_callback,
            on_human_message=message_callback,
            on_ai_message=message_callback,
            on_tool_message=message_callback,
            on_stream_token=partial_callback,
            on_thread_update=thread_callback,
            on_error=error_callback,
            on_media_artifacts=media_callback,
        )

        # Test each callback
        await handlers.on_status_change(
            thread_id, "thinking", "Processing request", "Hello"
        )
        await handlers.on_human_message(mock_message)
        await handlers.on_ai_message(mock_message)
        await handlers.on_tool_message(mock_message)
        await handlers.on_stream_token(mock_partial)
        await handlers.on_thread_update(mock_thread)
        await handlers.on_error("Test error", "test_user")
        await handlers.on_media_artifacts(mock_artifacts)

        # Verify all callbacks were called with correct parameters
        assert len(invocations) == 8
        assert invocations[0] == (
            "status",
            thread_id,
            "thinking",
            "Processing request",
            "Hello",
        )
        assert invocations[1] == ("message", mock_message)
        assert invocations[2] == ("message", mock_message)
        assert invocations[3] == ("message", mock_message)
        assert invocations[4] == ("partial", mock_partial)
        assert invocations[5] == ("thread", mock_thread)
        assert invocations[6] == ("error", "Test error", "test_user")
        assert invocations[7] == ("media", mock_artifacts)

    def test_callback_optionality(self) -> None:
        """Test that None callbacks don't cause issues."""
        handlers = CallbackHandlers()

        # All callbacks should be None and not raise errors when accessed
        assert handlers.on_status_change is None
        assert handlers.on_human_message is None
        assert handlers.on_ai_message is None
        assert handlers.on_tool_message is None
        assert handlers.on_stream_token is None
        assert handlers.on_thread_update is None
        assert handlers.on_error is None
        assert handlers.on_media_artifacts is None


if __name__ == "__main__":
    pytest.main(["-v", __file__])
