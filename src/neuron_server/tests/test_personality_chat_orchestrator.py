"""Tests for the PersonalityChatOrchestrator class."""

import unittest.mock
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
from langchain_core.runnables import Runnable

from neuron_server.models.personality_message_model import PersonalityMessageModel
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.models.user_model import UserModel
from neuron_server.services.personality_chat_orchestrator import (
    PersonalityChatOrchestrator,
    PersonalityDirectedAnalysis,
)


class TestPersonalityChatOrchestrator:
    """Test suite for PersonalityChatOrchestrator."""

    @pytest.fixture
    def orchestrator(self) -> PersonalityChatOrchestrator:
        """Create an orchestrator instance for testing."""
        return PersonalityChatOrchestrator()

    @pytest.fixture
    def sample_personality_id(self) -> UUID:
        """Create a sample personality ID."""
        return uuid4()

    @pytest.fixture
    def sample_user_id(self) -> str:
        """Create a sample user ID."""
        return "test_user_123"

    @pytest.fixture
    def sample_message_id(self) -> UUID:
        """Create a sample message ID."""
        return uuid4()

    @pytest.fixture
    def mock_personality(self) -> PersonalityModel:
        """Create a mock personality."""
        personality = MagicMock(spec=PersonalityModel)
        personality.id = uuid4()
        personality.name = "TestBot"
        personality.context = "You are a helpful AI assistant."
        personality.status = ""
        return personality

    @pytest.fixture
    def mock_user_message(
        self, sample_message_id: UUID, sample_user_id: str
    ) -> PersonalityMessageModel:
        """Create a mock user message."""
        message = MagicMock(spec=PersonalityMessageModel)
        message.id = sample_message_id
        message.user_id = sample_user_id
        message.content = "Hello, can you help me?"
        message.personality_room_id = uuid4()  # Add room ID
        message.created_at = MagicMock()
        message.created_at.isoformat.return_value = "2023-01-01T12:00:00"
        return message

    @pytest.fixture
    def mock_user(self, sample_user_id: str) -> UserModel:
        """Create a mock user."""
        user = MagicMock(spec=UserModel)
        user.id = sample_user_id
        user.nickname = "TestUser"
        return user

    @pytest.fixture
    def mock_users_dict(self, mock_user: UserModel) -> dict[str, UserModel]:
        """Create a mock users dictionary."""
        return {mock_user.id: mock_user}

    def test_count_message_tokens(
        self, orchestrator: PersonalityChatOrchestrator
    ) -> None:
        """Test token counting functionality."""
        # Test with simple message
        simple_message = "Hello world"
        token_count = orchestrator.count_message_tokens(simple_message)
        assert isinstance(token_count, int)
        assert token_count > 0

        # Test with empty message
        empty_count = orchestrator.count_message_tokens("")
        assert empty_count == 0

        # Test that longer messages have more tokens
        long_message = "This is a much longer message with many more words"
        long_count = orchestrator.count_message_tokens(long_message)
        assert long_count > token_count

    @pytest.mark.asyncio
    async def test_broadcast_personality_status_update(
        self, orchestrator: PersonalityChatOrchestrator, sample_personality_id: UUID
    ) -> None:
        """Test broadcasting personality status updates."""
        with patch(
            "neuron_server.services.personality_chat_orchestrator.secure_pubsub"
        ) as mock_pubsub:
            mock_pubsub.publish_personality_event = AsyncMock()

            await orchestrator.broadcast_personality_status_update(
                sample_personality_id, "thinking"
            )

            # Verify pubsub was called
            mock_pubsub.publish_personality_event.assert_called_once()
            call_args = mock_pubsub.publish_personality_event.call_args
            assert call_args[0][0] == sample_personality_id
            assert call_args[0][1].status == "thinking"

    @pytest.mark.asyncio
    async def test_get_personality_users_dict(
        self,
        orchestrator: PersonalityChatOrchestrator,
        sample_personality_id: UUID,
        mock_user: UserModel,
    ) -> None:
        """Test getting personality users as dictionary."""
        with (
            patch(
                "neuron_server.models.personality_user_model.PersonalityUserModel.get_personality_users"
            ) as mock_get_users,
            patch(
                "neuron_server.models.user_model.UserModel.get_by_ids"
            ) as mock_get_by_ids,
        ):
            # Mock personality users
            mock_personality_user = MagicMock()
            mock_personality_user.user_id = mock_user.id
            mock_get_users.return_value = [mock_personality_user]

            # Mock user lookup
            mock_get_by_ids.return_value = [mock_user]

            result = await orchestrator.get_personality_users_dict(
                sample_personality_id
            )

            assert isinstance(result, dict)
            assert mock_user.id in result
            assert result[mock_user.id] == mock_user

            # Verify calls
            mock_get_users.assert_called_once_with(sample_personality_id)
            mock_get_by_ids.assert_called_once_with(user_ids=[mock_user.id])

    @pytest.mark.asyncio
    async def test_get_personality_fast_model(
        self, orchestrator: PersonalityChatOrchestrator, sample_personality_id: UUID
    ) -> None:
        """Test getting fast model for personality."""
        with patch(
            "neuron_server.models.provider_model.ProviderModelModel.get_active_llm"
        ) as mock_get_llm:
            mock_llm = MagicMock()
            mock_fast_model = MagicMock(spec=Runnable)
            mock_llm.fast_model = mock_fast_model
            mock_get_llm.return_value = mock_llm

            result = await orchestrator.get_personality_fast_model(
                sample_personality_id
            )

            assert result == mock_fast_model
            mock_get_llm.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_personality_fast_model_no_fast_model(
        self, orchestrator: PersonalityChatOrchestrator, sample_personality_id: UUID
    ) -> None:
        """Test error when no fast model available."""
        with patch(
            "neuron_server.models.provider_model.ProviderModelModel.get_active_llm"
        ) as mock_get_llm:
            mock_llm = MagicMock()
            mock_llm.fast_model = None
            mock_get_llm.return_value = mock_llm

            with pytest.raises(ValueError, match="No fast model available"):
                await orchestrator.get_personality_fast_model(sample_personality_id)

    @pytest.mark.asyncio
    async def test_convert_to_chat_history_empty(
        self,
        orchestrator: PersonalityChatOrchestrator,
        mock_personality: PersonalityModel,
    ) -> None:
        """Test converting empty message list to chat history."""
        result = await orchestrator.convert_to_chat_history([], mock_personality, {})

        assert "<chat_history>" in result
        assert "No previous messages." in result

    @pytest.mark.asyncio
    async def test_convert_to_chat_history_with_messages(
        self,
        orchestrator: PersonalityChatOrchestrator,
        mock_personality: PersonalityModel,
        mock_user: UserModel,
        mock_users_dict: dict[str, UserModel],
    ) -> None:
        """Test converting messages to chat history XML."""
        # Create user message
        user_message = MagicMock(spec=PersonalityMessageModel)
        user_message.id = uuid4()
        user_message.user_id = mock_user.id
        user_message.content = "Hello bot"
        user_message.created_at = MagicMock()
        user_message.created_at.isoformat.return_value = "2023-01-01T12:00:00"

        # Create AI message
        ai_message = MagicMock(spec=PersonalityMessageModel)
        ai_message.id = uuid4()
        ai_message.user_id = None
        ai_message.content = "Hello user"
        ai_message.created_at = MagicMock()
        ai_message.created_at.isoformat.return_value = "2023-01-01T12:01:00"

        messages = [user_message, ai_message]

        # Mock the media item fetch to return empty lists
        with patch(
            "neuron_server.models.personality_message_media_item_model.PersonalityMessageMediaItemModel.get_media_for_message",
            return_value=[],
        ):
            result = await orchestrator.convert_to_chat_history(
                messages, mock_personality, mock_users_dict
            )

        assert "<chat_history>" in result
        assert f'username="{mock_user.nickname}"' in result
        assert f'username="{mock_personality.name}"' in result
        assert "Hello bot" in result
        assert "Hello user" in result
        assert 'type="user"' in result
        assert 'type="personality"' in result
        # Check for new content structure
        assert "<content>" in result
        assert "</content>" in result

    @pytest.mark.asyncio
    async def test_convert_to_chat_history_with_media_items(
        self,
        orchestrator: PersonalityChatOrchestrator,
        mock_personality: PersonalityModel,
        mock_user: UserModel,
        mock_users_dict: dict[str, UserModel],
    ) -> None:
        """Test converting messages with media items to chat history XML."""
        # Create message with media
        message_with_media = MagicMock(spec=PersonalityMessageModel)
        message_with_media.id = uuid4()
        message_with_media.user_id = mock_user.id
        message_with_media.content = "Check out this image!"
        message_with_media.created_at = MagicMock()
        message_with_media.created_at.isoformat.return_value = "2023-01-01T12:00:00"

        # Create mock media items
        media_item1 = MagicMock()
        media_item1.url = "https://example.com/image1.jpg"
        media_item1.media_type = "image"
        media_item1.name = "Cool Image"
        media_item1.description = "A really cool image"

        media_item2 = MagicMock()
        media_item2.url = "https://example.com/video1.mp4"
        media_item2.media_type = "video"
        media_item2.name = "Cool Video"
        media_item2.description = ""

        messages = [message_with_media]

        # Mock the media item fetch to return our mock media items
        with patch(
            "neuron_server.models.personality_message_media_item_model.PersonalityMessageMediaItemModel.get_media_for_message",
            return_value=[media_item1, media_item2],
        ):
            result = await orchestrator.convert_to_chat_history(
                messages, mock_personality, mock_users_dict
            )

        assert "<chat_history>" in result
        assert "<content>Check out this image!</content>" in result
        assert "<media>" in result
        assert "</media>" in result
        assert 'url="https://example.com/image1.jpg"' in result
        assert 'type="image"' in result
        assert 'name="Cool Image"' in result
        assert 'description="A really cool image"' in result
        assert 'url="https://example.com/video1.mp4"' in result
        assert 'type="video"' in result
        assert 'name="Cool Video"' in result
        # Description should not be included when empty
        assert 'description=""' not in result

    @pytest.mark.asyncio
    async def test_convert_to_chat_history_with_long_description(
        self,
        orchestrator: PersonalityChatOrchestrator,
        mock_personality: PersonalityModel,
        mock_user: UserModel,
        mock_users_dict: dict[str, UserModel],
    ) -> None:
        """Test that long media descriptions are truncated to 1000 characters."""
        # Create message with media having a very long description
        message_with_media = MagicMock(spec=PersonalityMessageModel)
        message_with_media.id = uuid4()
        message_with_media.user_id = mock_user.id
        message_with_media.content = "Check out this document!"
        message_with_media.created_at = MagicMock()
        message_with_media.created_at.isoformat.return_value = "2023-01-01T12:00:00"

        # Create mock media item with very long description (over 1000 chars)
        long_description = "A" * 1500  # 1500 characters
        media_item = MagicMock()
        media_item.url = "https://example.com/document.pdf"
        media_item.media_type = "document"
        media_item.name = "Long Document"
        media_item.description = long_description

        messages = [message_with_media]

        # Mock the media item fetch to return our mock media item
        with patch(
            "neuron_server.models.personality_message_media_item_model.PersonalityMessageMediaItemModel.get_media_for_message",
            return_value=[media_item],
        ):
            result = await orchestrator.convert_to_chat_history(
                messages, mock_personality, mock_users_dict
            )

        # Check that description is truncated to 1000 chars + "..."
        assert "<media>" in result
        expected_truncated = "A" * 1000 + "..."
        assert f'description="{expected_truncated}"' in result
        # Ensure the full long description is NOT in the result
        assert long_description not in result

    @pytest.mark.asyncio
    async def test_analyze_message_direction_directed(
        self,
        orchestrator: PersonalityChatOrchestrator,
        sample_personality_id: UUID,
        mock_user_message: PersonalityMessageModel,
        mock_personality: PersonalityModel,
    ) -> None:
        """Test analyzing message direction when directed at personality."""
        with (
            patch.object(orchestrator, "get_personality_fast_model") as mock_get_model,
            patch.object(orchestrator, "get_personality_users_dict") as mock_get_users,
            patch.object(
                orchestrator, "get_token_limited_message_history"
            ) as mock_get_history,
            patch.object(
                orchestrator, "convert_to_chat_history"
            ) as mock_convert_history,
        ):
            # Setup mocks
            mock_fast_model = MagicMock()
            mock_structured_model = MagicMock()
            mock_fast_model.with_structured_output = MagicMock(
                return_value=mock_structured_model
            )
            mock_get_model.return_value = mock_fast_model

            mock_get_users.return_value = {}
            mock_get_history.return_value = []
            mock_convert_history.return_value = (
                "<chat_history>No previous messages.</chat_history>"
            )

            # Mock analysis result
            expected_analysis = PersonalityDirectedAnalysis(
                is_directed=True,
                confidence=0.8,
                reasoning="Message directly addresses the bot",
                quick_response=None,
                should_use_quick_response=False,
            )
            mock_structured_model.ainvoke = AsyncMock(return_value=expected_analysis)

            result = await orchestrator.analyze_message_direction(
                sample_personality_id, mock_user_message, mock_personality
            )

            assert isinstance(result, PersonalityDirectedAnalysis)
            assert result.is_directed is True
            assert result.confidence == 0.8
            assert result.reasoning == "Message directly addresses the bot"

    @pytest.mark.asyncio
    async def test_analyze_message_direction_busy_personality(
        self,
        orchestrator: PersonalityChatOrchestrator,
        sample_personality_id: UUID,
        mock_user_message: PersonalityMessageModel,
        mock_personality: PersonalityModel,
    ) -> None:
        """Test analyzing message direction when personality is busy."""
        mock_personality.status = "working on something"

        with (
            patch.object(orchestrator, "get_personality_fast_model") as mock_get_model,
            patch.object(orchestrator, "get_personality_users_dict") as mock_get_users,
            patch.object(
                orchestrator, "get_token_limited_message_history"
            ) as mock_get_history,
            patch.object(
                orchestrator, "convert_to_chat_history"
            ) as mock_convert_history,
        ):
            # Setup mocks
            mock_fast_model = MagicMock()
            mock_structured_model = MagicMock()
            mock_fast_model.with_structured_output = MagicMock(
                return_value=mock_structured_model
            )
            mock_get_model.return_value = mock_fast_model

            mock_get_users.return_value = {}
            mock_get_history.return_value = []
            mock_convert_history.return_value = (
                "<chat_history>No previous messages.</chat_history>"
            )

            # Mock analysis result with quick response
            expected_analysis = PersonalityDirectedAnalysis(
                is_directed=True,
                confidence=0.9,
                reasoning="Direct question but I'm busy",
                quick_response="I'm currently working on something, please wait.",
                should_use_quick_response=True,
            )
            mock_structured_model.ainvoke = AsyncMock(return_value=expected_analysis)

            result = await orchestrator.analyze_message_direction(
                sample_personality_id,
                mock_user_message,
                mock_personality,
                "working on something",
            )

            assert result.should_use_quick_response is True
            assert result.quick_response is not None

            # Verify the prompt included busy state information
            call_args = mock_structured_model.ainvoke.call_args[0][0]
            prompt_content = call_args[0].content
            assert "BUSY STATE HANDLING" in prompt_content
            assert "working on something" in prompt_content

    @pytest.mark.asyncio
    async def test_generate_personality_response(
        self,
        orchestrator: PersonalityChatOrchestrator,
        sample_personality_id: UUID,
        mock_personality: PersonalityModel,
        sample_user_id: str,
    ) -> None:
        """Test generating personality response."""
        with patch(
            "neuron_server.services.personality_chat_orchestrator.execute_agent_with_messages_streaming"
        ) as mock_execute:
            # Mock agent response - streaming version returns a tuple
            mock_execute.return_value = ("I'd be happy to help you!", [])

            # Add room_id to the call
            room_id = UUID("e9b0a1c2-3d4e-5f6a-7a8b-9c0d1e2f3a4b")

            result = await orchestrator.generate_personality_response(
                personality_id=sample_personality_id,
                room_id=room_id,
                personality=mock_personality,
                chat_history="<chat_history>Test history</chat_history>",
                latest_message="Can you help me?",
                user_id=sample_user_id,
                username="TestUser",
            )

            assert isinstance(result, tuple)
            assert len(result) == 2
            response_text, media_artifacts = result

            assert response_text == "I'd be happy to help you!"
            assert isinstance(media_artifacts, list)
            assert len(media_artifacts) == 0  # No tool calls in this test

            # Verify agent was called with correct parameters
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            # The streaming version uses keyword arguments
            kwargs = call_args[1]
            assert "messages" in kwargs
            assert len(kwargs["messages"]) > 0  # Has messages
            assert kwargs["personality_id"] == sample_personality_id
            assert kwargs["user_id"] == sample_user_id
            assert kwargs["username"] == "TestUser"
            # Check that status_callback was provided
            assert "status_callback" in kwargs
            assert kwargs["status_callback"] is not None

    @pytest.mark.asyncio
    async def test_create_and_broadcast_personality_response(
        self,
        orchestrator: PersonalityChatOrchestrator,
        sample_personality_id: UUID,
        sample_user_id: str,
    ) -> None:
        """Test creating and broadcasting personality response."""
        with (
            patch(
                "neuron_server.models.personality_message_model.PersonalityMessageModel.create"
            ) as mock_create,
            patch(
                "neuron_server.services.personality_chat_orchestrator.secure_pubsub"
            ) as mock_pubsub,
        ):
            # Mock message creation
            mock_message = MagicMock()
            mock_message.id = uuid4()
            mock_message.content = "Test response"
            mock_message.user_id = None
            mock_message.created_at.isoformat.return_value = "2023-01-01T12:00:00"
            mock_message.updated_at.isoformat.return_value = "2023-01-01T12:00:00"
            mock_create.return_value = mock_message

            mock_pubsub.publish_personality_room_message = AsyncMock()

            room_id = uuid4()
            await orchestrator.create_and_broadcast_personality_response(
                sample_personality_id, room_id, "Test response", sample_user_id
            )

            # Verify message was created
            mock_create.assert_called_once()
            create_args = mock_create.call_args[1]["params"]
            assert create_args.personality_id == sample_personality_id
            assert create_args.content == "Test response"
            assert create_args.user_id is None  # AI message

            # Verify broadcast
            mock_pubsub.publish_personality_room_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_with_generation(
        self,
        orchestrator: PersonalityChatOrchestrator,
        sample_personality_id: UUID,
        mock_personality: PersonalityModel,
        sample_user_id: str,
    ) -> None:
        """Test updating status with generation."""
        with (
            patch.object(
                orchestrator, "generate_personality_status_message"
            ) as mock_generate,
            patch(
                "neuron_server.models.personality_room_model.PersonalityRoomModel.update_status"
            ) as mock_update,
            patch.object(
                orchestrator, "broadcast_personality_room_status_update"
            ) as mock_broadcast,
        ):
            mock_generate.return_value = "thinking deeply"
            mock_fast_model = MagicMock(spec=Runnable)
            room_id = uuid4()

            await orchestrator.update_status_with_generation(
                personality_id=sample_personality_id,
                room_id=room_id,
                fast_model=mock_fast_model,
                personality=mock_personality,
                chat_history="<chat_history>Test</chat_history>",
                latest_message="Test message",
                user_id=sample_user_id,
            )

            # Verify status generation
            mock_generate.assert_called_once()

            # Verify status update
            mock_update.assert_called_once_with(room_id, "thinking deeply")

            # Verify broadcast
            mock_broadcast.assert_called_once_with(
                sample_personality_id, room_id, "thinking deeply"
            )

    @pytest.mark.asyncio
    async def test_process_user_message_directed_response(
        self,
        orchestrator: PersonalityChatOrchestrator,
        sample_personality_id: UUID,
        sample_message_id: UUID,
        mock_personality: PersonalityModel,
        mock_user_message: PersonalityMessageModel,
        mock_users_dict: dict[str, UserModel],
    ) -> None:
        """Test processing user message that generates a response."""
        with (
            patch(
                "neuron_server.models.personality_message_model.PersonalityMessageModel.get"
            ) as mock_get_message,
            patch(
                "neuron_server.models.personality_model.PersonalityModel.get"
            ) as mock_get_personality,
            patch(
                "neuron_server.models.personality_room_model.PersonalityRoomModel.get"
            ) as mock_get_room,
            patch(
                "neuron_server.models.personality_room_model.PersonalityRoomModel.update_status"
            ) as mock_update_room_status,
            patch.object(
                orchestrator, "broadcast_personality_room_status_update"
            ) as mock_broadcast,
            patch.object(orchestrator, "analyze_message_direction") as mock_analyze,
            patch.object(orchestrator, "get_personality_users_dict") as mock_get_users,
            patch.object(
                orchestrator, "get_token_limited_message_history"
            ) as mock_get_history,
            patch.object(orchestrator, "convert_to_chat_history") as mock_convert,
            patch.object(orchestrator, "get_personality_fast_model") as mock_get_model,
            patch.object(
                orchestrator, "generate_personality_response"
            ) as mock_generate,
            patch.object(
                orchestrator, "create_and_broadcast_personality_response"
            ) as mock_create_broadcast,
        ):
            # Setup mocks
            mock_get_message.return_value = mock_user_message
            mock_get_personality.return_value = mock_personality

            # Mock room
            mock_room = MagicMock()
            mock_room.id = mock_user_message.personality_room_id
            mock_room.name = "Test Room"
            mock_get_room.return_value = mock_room

            mock_get_users.return_value = mock_users_dict
            mock_get_history.return_value = []
            mock_convert.return_value = "<chat_history>Test</chat_history>"
            mock_get_model.return_value = MagicMock(spec=Runnable)

            # Mock analysis - message is directed and confident
            mock_analysis = PersonalityDirectedAnalysis(
                is_directed=True,
                confidence=0.8,
                reasoning="Direct question",
                quick_response=None,
                should_use_quick_response=False,
                suggested_room_name=None,
                should_update_room_name=False,
            )
            mock_analyze.return_value = mock_analysis

            # Mock response generation
            mock_generate.return_value = ("Here's my response", [])

            await orchestrator.process_user_message(
                sample_personality_id, sample_message_id
            )

            # Verify room status updates
            assert mock_update_room_status.call_count >= 2  # contemplating and clear
            assert mock_broadcast.call_count >= 2

            # Verify analysis was called
            mock_analyze.assert_called_once()

            # Verify response generation and broadcast
            mock_generate.assert_called_once()
            mock_create_broadcast.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_user_message_quick_response(
        self,
        orchestrator: PersonalityChatOrchestrator,
        sample_personality_id: UUID,
        sample_message_id: UUID,
        mock_personality: PersonalityModel,
        mock_user_message: PersonalityMessageModel,
    ) -> None:
        """Test processing user message that gets a quick response."""
        with (
            patch(
                "neuron_server.models.personality_message_model.PersonalityMessageModel.get"
            ) as mock_get_message,
            patch(
                "neuron_server.models.personality_model.PersonalityModel.get"
            ) as mock_get_personality,
            patch(
                "neuron_server.models.personality_room_model.PersonalityRoomModel.get"
            ) as mock_get_room,
            patch(
                "neuron_server.models.personality_room_model.PersonalityRoomModel.update_status"
            ),
            patch.object(orchestrator, "broadcast_personality_room_status_update"),
            patch.object(orchestrator, "analyze_message_direction") as mock_analyze,
            patch.object(
                orchestrator, "create_and_broadcast_personality_response"
            ) as mock_create_broadcast,
        ):
            # Setup mocks
            mock_get_message.return_value = mock_user_message
            mock_get_personality.return_value = mock_personality

            # Mock room
            mock_room = MagicMock()
            mock_room.id = mock_user_message.personality_room_id
            mock_room.name = "Test Room"
            mock_get_room.return_value = mock_room

            # Mock analysis - quick response needed
            mock_analysis = PersonalityDirectedAnalysis(
                is_directed=True,
                confidence=0.9,
                reasoning="Question while busy",
                quick_response="I'm busy right now, please wait.",
                should_use_quick_response=True,
                suggested_room_name=None,
                should_update_room_name=False,
            )
            mock_analyze.return_value = mock_analysis

            await orchestrator.process_user_message(
                sample_personality_id, sample_message_id
            )

            # Verify quick response was broadcast
            mock_create_broadcast.assert_called_once()
            call_args = mock_create_broadcast.call_args
            assert call_args[0][2] == "I'm busy right now, please wait."

    @pytest.mark.asyncio
    async def test_process_user_message_not_directed(
        self,
        orchestrator: PersonalityChatOrchestrator,
        sample_personality_id: UUID,
        sample_message_id: UUID,
        mock_personality: PersonalityModel,
        mock_user_message: PersonalityMessageModel,
    ) -> None:
        """Test processing user message that is not directed at personality."""
        with (
            patch(
                "neuron_server.models.personality_message_model.PersonalityMessageModel.get"
            ) as mock_get_message,
            patch(
                "neuron_server.models.personality_model.PersonalityModel.get"
            ) as mock_get_personality,
            patch(
                "neuron_server.models.personality_room_model.PersonalityRoomModel.get"
            ) as mock_get_room,
            patch(
                "neuron_server.models.personality_room_model.PersonalityRoomModel.update_status"
            ) as mock_update_status,
            patch.object(orchestrator, "broadcast_personality_room_status_update"),
            patch.object(orchestrator, "analyze_message_direction") as mock_analyze,
            patch.object(
                orchestrator, "generate_personality_response"
            ) as mock_generate,
        ):
            # Setup mocks
            mock_get_message.return_value = mock_user_message
            mock_get_personality.return_value = mock_personality

            # Mock room
            mock_room = MagicMock()
            mock_room.id = mock_user_message.personality_room_id
            mock_room.name = "Test Room"
            mock_get_room.return_value = mock_room

            # Mock analysis - not directed
            mock_analysis = PersonalityDirectedAnalysis(
                is_directed=False,
                confidence=0.2,
                reasoning="General conversation",
                quick_response=None,
                should_use_quick_response=False,
                suggested_room_name=None,
                should_update_room_name=False,
            )
            mock_analyze.return_value = mock_analysis

            await orchestrator.process_user_message(
                sample_personality_id, sample_message_id
            )

            # Verify no response was generated
            mock_generate.assert_not_called()

            # Verify room status was cleared
            mock_update_status.assert_called_with(
                mock_user_message.personality_room_id, ""
            )

    @pytest.mark.asyncio
    async def test_process_user_message_with_room_name_update(
        self,
        orchestrator: PersonalityChatOrchestrator,
        sample_personality_id: UUID,
        sample_message_id: UUID,
        mock_personality: PersonalityModel,
        mock_user_message: PersonalityMessageModel,
        mock_users_dict: dict[str, UserModel],
    ) -> None:
        """Test processing user message that triggers room name update."""
        with (
            patch(
                "neuron_server.models.personality_message_model.PersonalityMessageModel.get"
            ) as mock_get_message,
            patch(
                "neuron_server.models.personality_model.PersonalityModel.get"
            ) as mock_get_personality,
            patch(
                "neuron_server.models.personality_room_model.PersonalityRoomModel.get"
            ) as mock_get_room,
            patch(
                "neuron_server.models.personality_room_model.PersonalityRoomModel.update_status"
            ),
            patch(
                "neuron_server.models.personality_room_model.PersonalityRoomModel.update"
            ) as mock_update_room,
            patch.object(orchestrator, "broadcast_personality_room_status_update"),
            patch(
                "neuron_server.services.personality_chat_orchestrator.secure_pubsub"
            ) as mock_pubsub,
            patch.object(orchestrator, "analyze_message_direction") as mock_analyze,
            patch.object(orchestrator, "get_personality_users_dict") as mock_get_users,
            patch.object(
                orchestrator, "get_token_limited_message_history"
            ) as mock_get_history,
            patch.object(orchestrator, "convert_to_chat_history") as mock_convert,
            patch.object(orchestrator, "get_personality_fast_model") as mock_get_model,
            patch.object(
                orchestrator, "generate_personality_response"
            ) as mock_generate,
            patch.object(
                orchestrator, "create_and_broadcast_personality_response"
            ) as mock_create_broadcast,
        ):
            # Setup mocks
            mock_get_message.return_value = mock_user_message
            mock_get_personality.return_value = mock_personality

            # Mock room with generic name
            mock_room = MagicMock()
            mock_room.id = mock_user_message.personality_room_id
            mock_room.name = "New Chat"
            mock_room.type = "private"
            mock_get_room.return_value = mock_room

            # Mock updated room
            mock_updated_room = MagicMock()
            mock_updated_room.id = mock_user_message.personality_room_id
            mock_updated_room.name = "Python Debugging Help"
            mock_updated_room.type = "private"
            mock_update_room.return_value = mock_updated_room

            mock_get_users.return_value = mock_users_dict
            mock_get_history.return_value = []
            mock_convert.return_value = "<chat_history>Test</chat_history>"
            # Create a mock model with with_structured_output method
            mock_model = MagicMock(spec=Runnable)
            mock_structured = MagicMock()
            mock_structured.ainvoke = AsyncMock(
                return_value=MagicMock(status="thinking")
            )
            mock_model.with_structured_output = MagicMock(return_value=mock_structured)
            mock_get_model.return_value = mock_model
            mock_pubsub.publish_personality_room_message = AsyncMock()

            # Mock analysis - message is directed and room name should update
            mock_analysis = PersonalityDirectedAnalysis(
                is_directed=True,
                confidence=0.9,
                reasoning="User asking for Python debugging help",
                quick_response=None,
                should_use_quick_response=False,
                suggested_room_name="Python Debugging Help",
                should_update_room_name=True,
            )
            mock_analyze.return_value = mock_analysis

            # Mock response generation
            mock_generate.return_value = ("I'll help you debug your Python code.", [])

            await orchestrator.process_user_message(
                sample_personality_id, sample_message_id
            )

            # Verify room name was updated
            mock_update_room.assert_called_once()
            update_params = mock_update_room.call_args[0][0]
            assert update_params.room_id == mock_user_message.personality_room_id
            assert update_params.name == "Python Debugging Help"

            # Verify room update event was broadcast
            mock_pubsub.publish_personality_room_message.assert_any_call(
                sample_personality_id,
                mock_user_message.personality_room_id,
                unittest.mock.ANY,  # We'll check the event type below
            )

            # Check that a PersonalityRoomUpdatedEvent was broadcast
            calls = mock_pubsub.publish_personality_room_message.call_args_list
            room_update_call = None
            for call in calls:
                event = call[0][2]  # Third argument is the event
                if hasattr(event, "type") and event.type == "personality_room_updated":
                    room_update_call = call
                    break

            assert room_update_call is not None, (
                "PersonalityRoomUpdatedEvent not broadcast"
            )
            event = room_update_call[0][2]  # Third argument is the event
            assert event.room_id == mock_user_message.personality_room_id
            assert event.name == "Python Debugging Help"

            # Verify response was still generated
            mock_generate.assert_called_once()
            mock_create_broadcast.assert_called_once()
