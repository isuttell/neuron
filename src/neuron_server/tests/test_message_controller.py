from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from uuid import UUID, uuid4

import pytest
from quart import Quart
from sqlalchemy.ext.asyncio import AsyncSession
from werkzeug.exceptions import BadRequest, NotFound

from neuron_server.controllers import message_controller
from neuron_server.controllers.auth import TokenPayload
from neuron_server.controllers.events.message_events import CancelMessage, PostMessage
from neuron_server.models import ThreadModel
from neuron_server.models.message_model import MessageModel

# HTTP Status Codes
HTTP_CREATED = 201


@pytest.fixture
def mock_decode_token() -> AsyncMock:
    with patch("neuron_server.controllers.auth.decode_token") as mock:
        mock.return_value = TokenPayload(
            sub="test_user",
            user_id=str(uuid4()),
            nickname="test_user",
            email="test@example.com",
            picture=None,  # Add missing picture field
            roles=["user"],
            permissions=["read", "write"],
        )
        yield mock


@pytest.fixture
def mock_thread() -> MagicMock:
    thread = MagicMock(spec=ThreadModel)
    thread.id = uuid4()
    thread.user_id = str(uuid4())  # Add user_id attribute
    thread.model_dump.return_value = {
        "id": thread.id,
        "user_id": thread.user_id,
        "title": "Test Thread",
        "created_at": "2024-01-01T00:00:00Z",
    }
    return thread


@pytest.fixture
def mock_thread_model() -> AsyncMock:
    with patch("neuron_server.controllers.message_controller.ThreadModel") as mock:
        mock.get = AsyncMock()
        yield mock


@pytest.fixture
def mock_token() -> MagicMock:
    return MagicMock(user_id=uuid4(), nickname="test_user")


@pytest.fixture
def mock_file() -> MagicMock:
    file = MagicMock()
    file.filename = "test.jpg"
    return file


@pytest.fixture
def app() -> Quart:
    app = Quart(__name__)
    app.register_blueprint(message_controller.blueprint)
    return app


@pytest.fixture(autouse=True)
async def mock_db_session() -> AsyncGenerator[None, None]:
    """Mock the database session to prevent actual database connections."""
    session_mock = AsyncMock(spec=AsyncSession)

    # Create a context manager mock that returns the session mock
    cm_mock = AsyncMock()
    cm_mock.__aenter__.return_value = session_mock
    cm_mock.__aexit__.return_value = None

    # Define model paths for better line length control
    thread_model = "neuron_server.models.thread_model.get_session"
    message_model = "neuron_server.models.message_model.get_session"
    media_model = "neuron_server.models.media_item_model.get_session"
    thread_user_model = "neuron_server.models.thread_user_model.get_session"
    user_model = "neuron_server.models.user_model.get_session"

    # Patch the get_session function to return our mock
    with (
        patch(thread_model, return_value=cm_mock),
        patch(message_model, return_value=cm_mock),
        patch(media_model, return_value=cm_mock),
        patch(thread_user_model, return_value=cm_mock),
        patch(user_model, return_value=cm_mock),
    ):
        yield None


@pytest.mark.asyncio
async def test_get_thread_messages_success(
    app: Quart,
    mock_thread: MagicMock,
    mock_token: MagicMock,
    mock_decode_token: AsyncMock,
    mock_thread_model: AsyncMock,
) -> None:
    """Test successful retrieval of thread messages."""
    messages: list[MagicMock] = [
        MagicMock(
            spec=MessageModel,
            type="human",
            content="Hello",
            thread_id=mock_thread.id,
            created_at="2024-01-01T00:00:00Z",
            additional_kwargs={},
            model_dump=lambda: {
                "type": "human",
                "content": "Hello",
                "created_at": "2024-01-01T00:00:00Z",
            },
        )
    ]
    state = MagicMock(values={"messages": messages})

    mock_thread_model.get.return_value = mock_thread
    with patch(
        "neuron_server.controllers.message_controller.aget_state"
    ) as mock_get_state:
        mock_get_state.return_value = state
        with patch(
            "neuron_server.controllers.message_controller.MediaItemModel"
        ) as mock_media:
            mock_media.get_thread_media = AsyncMock(return_value=[])
            with patch(
                "neuron_server.controllers.message_controller.ThreadUserModel"
            ) as mock_thread_user:
                mock_thread_user.get_thread_users = AsyncMock(return_value=[])
                with patch(
                    "neuron_server.controllers.message_controller.UserModel"
                ) as mock_user_model:
                    mock_user_model.get_by_ids = AsyncMock(return_value=[])

                    async with app.test_request_context(
                        "/thread/123",
                        headers={
                            "Authorization": (
                                "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9"
                                ".eyJzdWIiOiJ0ZXN0In0.abc"
                            )
                        },
                    ):
                        # Mock auth token
                        app.request_class.token = mock_token

                        result = await message_controller.get_thread_messages(
                            mock_thread.id
                        )

                        assert "threads" in result
                        assert "messages" in result
                        assert "media" in result
                        assert len(result["messages"]) == 1
                        assert result["messages"][0]["content"] == "Hello"


@pytest.mark.asyncio
async def test_get_thread_messages_filters_hidden(
    app: Quart,
    mock_thread: MagicMock,
    mock_token: MagicMock,
    mock_decode_token: AsyncMock,
    mock_thread_model: AsyncMock,
) -> None:
    """Test that hidden messages are filtered out."""
    messages: list[MagicMock] = [
        MagicMock(
            spec=MessageModel,
            type="human",
            content="Hello",
            thread_id=mock_thread.id,
            created_at="2024-01-01T00:00:00Z",
            additional_kwargs={},
            model_dump=lambda: {
                "type": "human",
                "content": "Hello",
                "created_at": "2024-01-01T00:00:00Z",
            },
        ),
        MagicMock(
            spec=MessageModel,
            type="ai",
            content="[2024-01-01 00:00:00 UTC] [Test Assistant] ",
            thread_id=mock_thread.id,
            created_at="2024-01-01T00:00:01Z",
            additional_kwargs={"hidden": True},
            model_dump=lambda: {
                "type": "ai",
                "content": "[2024-01-01 00:00:00 UTC] [Test Assistant] ",
                "created_at": "2024-01-01T00:00:01Z",
                "additional_kwargs": {"hidden": True},
            },
        ),
        MagicMock(
            spec=MessageModel,
            type="ai",
            content="Hello! How can I help you?",
            thread_id=mock_thread.id,
            created_at="2024-01-01T00:00:02Z",
            additional_kwargs={},
            model_dump=lambda: {
                "type": "ai",
                "content": "Hello! How can I help you?",
                "created_at": "2024-01-01T00:00:02Z",
            },
        ),
    ]
    state = MagicMock(values={"messages": messages})

    mock_thread_model.get.return_value = mock_thread
    with patch(
        "neuron_server.controllers.message_controller.aget_state"
    ) as mock_get_state:
        mock_get_state.return_value = state
        with patch(
            "neuron_server.controllers.message_controller.MediaItemModel"
        ) as mock_media:
            mock_media.get_thread_media = AsyncMock(return_value=[])
            with patch(
                "neuron_server.controllers.message_controller.ThreadUserModel"
            ) as mock_thread_user:
                mock_thread_user.get_thread_users = AsyncMock(return_value=[])
                with patch(
                    "neuron_server.controllers.message_controller.UserModel"
                ) as mock_user_model:
                    mock_user_model.get_by_ids = AsyncMock(return_value=[])

                    async with app.test_request_context(
                        "/thread/123",
                        headers={
                            "Authorization": (
                                "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9"
                                ".eyJzdWIiOiJ0ZXN0In0.abc"
                            )
                        },
                    ):
                        # Mock auth token
                        app.request_class.token = mock_token

                        result = await message_controller.get_thread_messages(
                            mock_thread.id
                        )

                        # Should only have 2 messages (human and visible AI)
                        assert len(result["messages"]) == 2
                        assert result["messages"][0]["content"] == "Hello"
                        expected_msg = "Hello! How can I help you?"
                        assert result["messages"][1]["content"] == expected_msg
                        # Hidden message should not be in the results
                        assert not any(
                            "[Test Assistant]" in msg["content"]
                            for msg in result["messages"]
                        )


@pytest.mark.asyncio
async def test_get_thread_messages_not_found(
    app: Quart,
    mock_token: MagicMock,
    mock_decode_token: AsyncMock,
    mock_thread_model: AsyncMock,
) -> None:
    """Test handling of non-existent thread."""
    mock_thread_model.get.return_value = None

    async with app.test_request_context(
        "/thread/123",
        headers={
            "Authorization": (
                "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.abc"
            )
        },
    ):
        app.request_class.token = mock_token

        with pytest.raises(NotFound, match="Thread not found"):
            await message_controller.get_thread_messages(uuid4())


@pytest.mark.asyncio
async def test_process_message_request_text_only() -> None:
    """Test processing text-only message."""
    files: dict[str, Any] = {}
    form: dict[str, str] = {"prompt": "Hello world"}

    result = await message_controller.process_message_request(files, form)
    assert result.strip() == "Hello world"


@pytest.mark.asyncio
async def test_process_message_request_with_image(mock_file: MagicMock) -> None:
    """Test processing message with image upload."""
    with patch(
        "neuron_server.controllers.message_controller.process_uploaded_file"
    ) as mock_process:
        mock_process.return_value = ("test.jpg", ".jpg", "http://test.com/test.jpg")

        files: dict[str, MagicMock] = {"file": mock_file}
        form: dict[str, str] = {"prompt": "Check this image"}

        result = await message_controller.process_message_request(files, form)
        assert "Check this image" in result
        assert "test.jpg" in result
        assert "http://test.com/test.jpg" in result


@pytest.mark.asyncio
async def test_process_message_request_with_audio(mock_file: MagicMock) -> None:
    """Test processing message with audio upload."""
    with patch(
        "neuron_server.controllers.message_controller.process_uploaded_file"
    ) as mock_process:
        mock_process.return_value = ("test.webm", ".webm", "http://test.com/test.webm")
        with (
            patch("neuron_server.controllers.message_controller.client") as mock_client,
            patch("builtins.open", create=True) as mock_open,
        ):
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file
            mock_client.audio.transcriptions.create = AsyncMock(
                return_value="Transcribed text"
            )

            files: dict[str, MagicMock] = {"file": mock_file}
            form: dict[str, str] = {}

            result = await message_controller.process_message_request(files, form)
            assert result.strip() == "Transcribed text"


def test_format_ai_uploaded_file_image() -> None:
    """Test formatting image file for AI."""
    result = message_controller.format_ai_uploaded_file(
        "test.jpg", ".jpg", "http://test.com/test.jpg"
    )
    assert "![test.jpg](http://test.com/test.jpg)" in result


def test_format_ai_uploaded_file_audio() -> None:
    """Test formatting audio file for AI."""
    result = message_controller.format_ai_uploaded_file(
        "test.mp3", ".mp3", "http://test.com/test.mp3"
    )
    assert '<audio src="http://test.com/test.mp3">' in result


def test_format_ai_uploaded_file_video() -> None:
    """Test formatting video file for AI."""
    result = message_controller.format_ai_uploaded_file(
        "test.mp4", ".mp4", "http://test.com/test.mp4"
    )
    assert '<video src="http://test.com/test.mp4">' in result


def test_format_ai_uploaded_file_other() -> None:
    """Test formatting other file types for AI."""
    result = message_controller.format_ai_uploaded_file(
        "test.txt", ".txt", "http://test.com/test.txt"
    )
    assert "<http://test.com/test.txt>" in result


@pytest.mark.asyncio
async def test_post_thread_message_success(
    app: Quart,
    mock_thread: MagicMock,
    mock_token: MagicMock,
    mock_decode_token: AsyncMock,
    mock_thread_model: AsyncMock,
) -> None:
    """Test successful message posting."""
    mock_thread_model.get.return_value = mock_thread
    with patch("neuron_server.controllers.message_controller.agent") as mock_agent:
        mock_agent.astream = AsyncMock()

        async with app.test_request_context(
            f"/thread/{mock_thread.id}",
            method="POST",
            form={"personality_id": str(uuid4()), "prompt": "Hello"},
            headers={
                "Authorization": (
                    "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9"
                    ".eyJzdWIiOiJ0ZXN0In0.abc"
                )
            },
        ):
            app.request_class.token = mock_token

            result, status_code = await message_controller.post_thread_message(
                mock_thread.id
            )

            assert status_code == HTTP_CREATED
            assert result["status"] == "success"


@pytest.mark.asyncio
async def test_post_thread_message_no_personality(
    app: Quart,
    mock_thread: MagicMock,
    mock_token: MagicMock,
    mock_decode_token: AsyncMock,
    mock_thread_model: AsyncMock,
) -> None:
    """Test message posting without personality_id."""
    mock_thread_model.get.return_value = mock_thread

    async with app.test_request_context(
        f"/thread/{mock_thread.id}",
        method="POST",
        form={"prompt": "Hello"},
        headers={
            "Authorization": (
                "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.abc"
            )
        },
    ):
        app.request_class.token = mock_token

        with pytest.raises(BadRequest, match="personality_id is required"):
            await message_controller.post_thread_message(mock_thread.id)


@pytest.mark.asyncio
async def test_post_thread_message_no_content(
    app: Quart,
    mock_thread: MagicMock,
    mock_token: MagicMock,
    mock_decode_token: AsyncMock,
    mock_thread_model: AsyncMock,
) -> None:
    """Test message posting without content."""
    mock_thread_model.get.return_value = mock_thread

    async with app.test_request_context(
        f"/thread/{mock_thread.id}",
        method="POST",
        form={"personality_id": str(uuid4())},
        headers={
            "Authorization": (
                "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.abc"
            )
        },
    ):
        app.request_class.token = mock_token

        with pytest.raises(BadRequest, match="Either prompt or file is required"):
            await message_controller.post_thread_message(mock_thread.id)


@pytest.mark.asyncio
async def test_apost_message() -> None:
    """Test PostMessage event handler."""
    thread_id: UUID = uuid4()
    personality_id: UUID = uuid4()
    personality_id_str: str = str(personality_id)
    user_id = "test_user_123"

    # Create mock session
    mock_session = Mock()
    mock_session.user_id = user_id
    mock_session.nickname = "testuser"

    with (
        patch("neuron_server.controllers.message_controller.UUID") as mock_uuid,
        patch("neuron_server.controllers.message_controller.agent") as mock_agent,
        patch(
            "neuron_server.controllers.message_controller.permission_service"
        ) as mock_perm,
    ):
        mock_uuid.return_value = personality_id
        mock_agent.astream = AsyncMock()
        mock_perm.user_has_thread_access = AsyncMock(return_value=True)
        mock_perm.user_has_personality_access = AsyncMock(return_value=True)

        event = PostMessage(
            type="message",
            thread_id=thread_id,
            personality_id=personality_id_str,
            prompt="Test message",
        )

        await message_controller.apost_message(event, session=mock_session)

        mock_agent.astream.assert_called_once_with(
            {
                "thread_id": thread_id,
                "personality_id": personality_id,
                "user_id": user_id,
                "username": "testuser",
                "prompt": "Test message",
            }
        )


@pytest.mark.asyncio
async def test_acancel_message() -> None:
    """Test CancelMessage event handler."""
    thread_id = uuid4()
    user_id = "test_user_123"

    # Create mock session
    mock_session = Mock()
    mock_session.user_id = user_id

    event = CancelMessage(type="cancel", thread_id=thread_id)

    with (
        patch("neuron_server.controllers.message_controller.pubsub") as mock_pubsub,
        patch(
            "neuron_server.controllers.message_controller.permission_service"
        ) as mock_perm,
    ):
        mock_pubsub.publish = AsyncMock()
        mock_perm.user_has_thread_access = AsyncMock(return_value=True)

        await message_controller.acancel_message(event, session=mock_session)

        mock_pubsub.publish.assert_called_once_with("cancel", thread_id)


if __name__ == "__main__":
    pytest.main(["-v", __file__])
