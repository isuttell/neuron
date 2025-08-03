"""Tests for websocket callbacks."""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from neuron_server.controllers.events.message_events import (
    PartialMessage,
    ThreadMessage,
)
from neuron_server.llms.websocket_callbacks import (
    create_websocket_callbacks,
    on_ai_message,
    on_error,
    on_human_message,
    on_media_artifacts,
    on_status_change,
    on_stream_token,
    on_thread_update,
    on_tool_message,
)
from neuron_server.models.thread_model import ThreadModel
from neuron_server.tools.artifact_types import ToolMediaArtifact


class TestWebsocketCallbackFunctions:
    """Test individual websocket callback functions."""

    @pytest.mark.asyncio
    async def test_on_human_message(self) -> None:
        """Test on_human_message callback."""
        thread_id = uuid4()
        message = ThreadMessage(
            id=str(uuid4()),
            thread_id=thread_id,
            type="human",
            content="Hello",
        )

        with patch(
            "neuron_server.llms.websocket_callbacks.secure_pubsub"
        ) as mock_pubsub:
            mock_pubsub.publish_thread_message = AsyncMock()

            await on_human_message(message)

            mock_pubsub.publish_thread_message.assert_called_once()
            call_args = mock_pubsub.publish_thread_message.call_args[0][0]
            assert call_args.message is message

    @pytest.mark.asyncio
    async def test_on_ai_message(self) -> None:
        """Test on_ai_message callback."""
        thread_id = uuid4()
        message = ThreadMessage(
            id=str(uuid4()),
            thread_id=thread_id,
            type="ai",
            content="Hello back!",
        )

        with patch(
            "neuron_server.llms.websocket_callbacks.secure_pubsub"
        ) as mock_pubsub:
            mock_pubsub.publish_thread_message = AsyncMock()

            await on_ai_message(message)

            mock_pubsub.publish_thread_message.assert_called_once()
            call_args = mock_pubsub.publish_thread_message.call_args[0][0]
            assert call_args.message is message

    @pytest.mark.asyncio
    async def test_on_tool_message(self) -> None:
        """Test on_tool_message callback."""
        thread_id = uuid4()
        message = ThreadMessage(
            id=str(uuid4()),
            thread_id=thread_id,
            type="tool",
            content="Tool result",
        )

        with patch(
            "neuron_server.llms.websocket_callbacks.secure_pubsub"
        ) as mock_pubsub:
            mock_pubsub.publish_thread_message = AsyncMock()

            await on_tool_message(message)

            mock_pubsub.publish_thread_message.assert_called_once()
            call_args = mock_pubsub.publish_thread_message.call_args[0][0]
            assert call_args.message is message

    @pytest.mark.asyncio
    async def test_on_stream_token(self) -> None:
        """Test on_stream_token callback."""
        thread_id = uuid4()
        partial_message = PartialMessage(
            id=str(uuid4()),
            thread_id=thread_id,
            type="ai",
            content="Streaming text...",
            index=0,
            status="streaming",
            node="agent",
        )

        with patch(
            "neuron_server.llms.websocket_callbacks.secure_pubsub"
        ) as mock_pubsub:
            mock_pubsub.publish_partial_message = AsyncMock()

            await on_stream_token(partial_message)

            mock_pubsub.publish_partial_message.assert_called_once()
            call_args = mock_pubsub.publish_partial_message.call_args[0][0]
            assert call_args.message is partial_message

    @pytest.mark.asyncio
    async def test_on_thread_update(self) -> None:
        """Test on_thread_update callback."""
        from datetime import datetime

        thread = ThreadModel(
            id=uuid4(),
            name="Test Thread",
            status="thinking",
            personality_id=uuid4(),
            user_id="test_user",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "neuron_server.llms.websocket_callbacks.secure_pubsub"
        ) as mock_pubsub:
            mock_pubsub.publish_thread_update = AsyncMock()

            await on_thread_update(thread)

            mock_pubsub.publish_thread_update.assert_called_once()
            call_args = mock_pubsub.publish_thread_update.call_args[0][0]
            assert call_args.thread is thread

    @pytest.mark.asyncio
    async def test_on_error_with_user_id(self) -> None:
        """Test on_error callback with user_id."""
        error_message = "Something went wrong"
        user_id = "test_user"

        with patch(
            "neuron_server.llms.websocket_callbacks.secure_pubsub"
        ) as mock_pubsub:
            mock_pubsub.publish_error_to_user = AsyncMock()

            await on_error(error_message, user_id)

            mock_pubsub.publish_error_to_user.assert_called_once()
            call_args = mock_pubsub.publish_error_to_user.call_args
            assert call_args[0][0] == user_id
            assert call_args[0][1].message == error_message

    @pytest.mark.asyncio
    async def test_on_error_without_user_id(self) -> None:
        """Test on_error callback without user_id."""
        error_message = "Something went wrong"

        with patch(
            "neuron_server.llms.websocket_callbacks.secure_pubsub"
        ) as mock_pubsub:
            mock_pubsub.publish_error_to_user = AsyncMock()

            with patch("neuron_server.llms.websocket_callbacks.logger") as mock_logger:
                await on_error(error_message, None)

                # Should not publish error
                mock_pubsub.publish_error_to_user.assert_not_called()

                # Should log warning
                mock_logger.warning.assert_called_once_with(
                    "Could not send error to user: user_id not available"
                )

    @pytest.mark.asyncio
    async def test_on_media_artifacts(self) -> None:
        """Test on_media_artifacts callback."""
        from neuron_server.tools.artifact_types import ToolMediaItem

        artifacts = [
            ToolMediaArtifact(
                media_type="image",
                items=[
                    ToolMediaItem(
                        id=uuid4(),
                        url="test1.jpg",
                        name="test image 1",
                        description="test image 1 description",
                    )
                ],
            ),
            ToolMediaArtifact(
                media_type="audio",
                items=[
                    ToolMediaItem(
                        id=uuid4(),
                        url="test.mp3",
                        name="test audio",
                        description="test audio description",
                    )
                ],
            ),
        ]

        with patch("neuron_server.llms.websocket_callbacks.logger") as mock_logger:
            await on_media_artifacts(artifacts)

            # Should log debug message about artifacts
            mock_logger.debug.assert_called_once_with(
                "Media artifacts callback received 2 artifacts"
            )

    @pytest.mark.asyncio
    async def test_on_status_change(self) -> None:
        """Test on_status_change callback."""
        thread_id = uuid4()
        raw_status = "thinking"
        generated_message = "Processing your request..."
        human_message = "Hello"

        # Mock ThreadModel
        from datetime import datetime

        mock_thread = ThreadModel(
            id=thread_id,
            name="Test Thread",
            status="idle",
            personality_id=uuid4(),
            user_id="test_user",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        with patch(
            "neuron_server.llms.websocket_callbacks.ThreadModel"
        ) as mock_thread_model:
            mock_thread_model.get = AsyncMock(return_value=mock_thread)
            mock_thread_model.set = AsyncMock()

            with patch(
                "neuron_server.llms.websocket_callbacks.on_thread_update"
            ) as mock_thread_update:
                mock_thread_update.return_value = AsyncMock()

                await on_status_change(
                    thread_id, raw_status, generated_message, human_message
                )

                # Should get thread
                mock_thread_model.get.assert_called_once_with(thread_id)

                # Should update thread status
                assert mock_thread.status == generated_message
                mock_thread_model.set.assert_called_once_with(
                    thread_id, "status", generated_message
                )

                # Should call thread update
                mock_thread_update.assert_called_once_with(mock_thread)

    @pytest.mark.asyncio
    async def test_on_status_change_no_thread(self) -> None:
        """Test on_status_change callback when thread doesn't exist."""
        thread_id = uuid4()

        with patch(
            "neuron_server.llms.websocket_callbacks.ThreadModel"
        ) as mock_thread_model:
            mock_thread_model.get = AsyncMock(return_value=None)
            mock_thread_model.set = AsyncMock()

            with patch(
                "neuron_server.llms.websocket_callbacks.on_thread_update"
            ) as mock_thread_update:
                await on_status_change(thread_id, "thinking", "Processing", "Hello")

                # Should try to get thread
                mock_thread_model.get.assert_called_once_with(thread_id)

                # Should not update or call thread update
                mock_thread_model.set.assert_not_called()
                mock_thread_update.assert_not_called()


class TestWebsocketCallbacksFactory:
    """Test websocket callbacks factory function."""

    def test_create_websocket_callbacks(self) -> None:
        """Test create_websocket_callbacks factory function."""
        handlers = create_websocket_callbacks()

        assert handlers.on_human_message is on_human_message
        assert handlers.on_ai_message is on_ai_message
        assert handlers.on_tool_message is on_tool_message
        assert handlers.on_stream_token is on_stream_token
        assert handlers.on_thread_update is on_thread_update
        assert handlers.on_error is on_error
        assert handlers.on_media_artifacts is on_media_artifacts
        assert handlers.on_status_change is on_status_change

    def test_create_websocket_callbacks_returns_working_handlers(self) -> None:
        """Test that factory returns working callback handlers."""
        handlers = create_websocket_callbacks()

        # All handlers should be callable
        assert callable(handlers.on_human_message)
        assert callable(handlers.on_ai_message)
        assert callable(handlers.on_tool_message)
        assert callable(handlers.on_stream_token)
        assert callable(handlers.on_thread_update)
        assert callable(handlers.on_error)
        assert callable(handlers.on_media_artifacts)
        assert callable(handlers.on_status_change)


class TestWebsocketCallbacksIntegration:
    """Test websocket callbacks integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_message_flow(self) -> None:
        """Test full message publishing flow."""
        thread_id = uuid4()
        handlers = create_websocket_callbacks()

        # Test human message
        human_message = ThreadMessage(
            id=str(uuid4()),
            thread_id=thread_id,
            type="human",
            content="Hello",
        )

        # Test AI message
        ai_message = ThreadMessage(
            id=str(uuid4()),
            thread_id=thread_id,
            type="ai",
            content="Hello back!",
        )

        with patch(
            "neuron_server.llms.websocket_callbacks.secure_pubsub"
        ) as mock_pubsub:
            mock_pubsub.publish_thread_message = AsyncMock()

            await handlers.on_human_message(human_message)
            await handlers.on_ai_message(ai_message)

            # Should have called publish twice
            assert mock_pubsub.publish_thread_message.call_count == 2

    @pytest.mark.asyncio
    async def test_error_handling_flow(self) -> None:
        """Test error handling flow."""
        handlers = create_websocket_callbacks()

        with patch(
            "neuron_server.llms.websocket_callbacks.secure_pubsub"
        ) as mock_pubsub:
            mock_pubsub.publish_error_to_user = AsyncMock()

            # Test with user_id
            await handlers.on_error("Test error", "test_user")
            mock_pubsub.publish_error_to_user.assert_called_once()

            # Test without user_id
            with patch("neuron_server.llms.websocket_callbacks.logger") as mock_logger:
                await handlers.on_error("Test error", None)
                mock_logger.warning.assert_called_once()


if __name__ == "__main__":
    pytest.main(["-v", __file__])
