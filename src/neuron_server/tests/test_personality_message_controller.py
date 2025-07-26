from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from quart import Quart

from neuron_server.api import app as neuron_app
from neuron_server.controllers.auth import TokenPayload
from neuron_server.controllers.events.room_events import (
    JoinPersonalityRoom,
    LeavePersonalityRoom,
)
from neuron_server.controllers.personality_message_controller import (
    ajoin_personality_room,
    aleave_personality_room,
    cleanup_user_personality_rooms,
)
from neuron_server.models.personality_message_model import PersonalityMessageModel
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.models.personality_user_model import PersonalityUserModel
from neuron_server.models.user_model import UserModel
from neuron_server.websocket_session_manager import WebSocketSession

# Constants
TEST_JWT_TOKEN = "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.abc"


@pytest.fixture
def app() -> Quart:
    """Return the Quart app for testing."""
    return neuron_app


@pytest.fixture
def mock_decode_token() -> AsyncMock:
    """Mock token decoding for authentication."""
    with patch("neuron_server.controllers.auth.decode_token") as mock:
        mock.return_value = TokenPayload(
            sub="test_user",
            user_id="test_user_id",
            nickname="test_user",
            email="test@example.com",
            picture=None,
            roles=["user"],
            permissions=["read"],
        )
        yield mock


@pytest.fixture
def mock_personality() -> MagicMock:
    """Mock personality object."""
    personality = MagicMock()
    personality.id = uuid4()
    personality.name = "Test Personality"
    personality.description = "Test Description"
    personality.model_dump.return_value = {
        "id": str(personality.id),
        "name": personality.name,
        "description": personality.description,
    }
    return personality


@pytest.fixture
def mock_message() -> MagicMock:
    """Mock personality message object."""
    message = MagicMock()
    message.id = uuid4()
    message.personality_id = uuid4()
    message.content = "Test message content"
    message.user_id = "test_user_id"
    message.created_at = MagicMock()
    message.updated_at = MagicMock()
    message.created_at.isoformat.return_value = "2023-01-01T00:00:00"
    message.updated_at.isoformat.return_value = "2023-01-01T00:00:00"
    message.model_dump.return_value = {
        "id": str(message.id),
        "personality_id": str(message.personality_id),
        "content": message.content,
        "user_id": message.user_id,
        "created_at": "2023-01-01T00:00:00",
        "updated_at": "2023-01-01T00:00:00",
    }
    return message


@pytest.fixture
def mock_user() -> MagicMock:
    """Mock user object."""
    user = MagicMock()
    user.id = "test_user_id"
    user.email = "test@example.com"
    user.nickname = "test_user"
    user.model_dump.return_value = {
        "id": user.id,
        "email": user.email,
        "nickname": user.nickname,
    }
    return user


@pytest.fixture
def mock_personality_user() -> MagicMock:
    """Mock personality user object."""
    personality_user = MagicMock()
    personality_user.id = uuid4()
    personality_user.personality_id = uuid4()
    personality_user.user_id = "test_user_id"
    personality_user.role = "user"
    return personality_user


@pytest.fixture
def mock_websocket_session() -> MagicMock:
    """Mock WebSocket session."""
    session = MagicMock(spec=WebSocketSession)
    session.user_id = "test_user_id"
    session.nickname = "test_user"
    return session


class TestPersonalityMessageController:
    """Tests for personality message REST endpoints."""

    @pytest.mark.asyncio
    async def test_get_personality_messages_success(
        self,
        app,
        mock_decode_token,
        mock_personality,
        mock_message,
        mock_user,
        mock_personality_user,
    ):
        """Test successfully getting personality messages."""
        personality_id = uuid4()

        with (
            patch.object(
                PersonalityModel, "get_for_user", return_value=mock_personality
            ),
            patch.object(PersonalityMessageModel, "list", return_value=[mock_message]),
            patch.object(
                PersonalityUserModel,
                "get_personality_users",
                return_value=[mock_personality_user],
            ),
            patch.object(UserModel, "get_by_ids", return_value=[mock_user]),
        ):
            async with app.test_client() as client:
                response = await client.get(
                    f"/api/personality-messages/{personality_id}?limit=50&offset=0",
                    headers={"Authorization": TEST_JWT_TOKEN},
                )

                assert response.status_code == 200
                data = await response.get_json()
                assert "personality_messages" in data
                assert "personality" in data
                assert "users" in data
                assert len(data["personality_messages"]) == 1
                assert len(data["users"]) == 1

    @pytest.mark.asyncio
    async def test_get_personality_messages_not_found(self, app, mock_decode_token):
        """Test getting messages for non-existent personality."""
        personality_id = uuid4()

        with patch.object(PersonalityModel, "get_for_user", return_value=None):
            async with app.test_client() as client:
                response = await client.get(
                    f"/api/personality-messages/{personality_id}",
                    headers={"Authorization": TEST_JWT_TOKEN},
                )

                assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_create_personality_message_success(
        self, app, mock_decode_token, mock_personality, mock_message
    ):
        """Test successfully creating a personality message."""
        personality_id = uuid4()

        with (
            patch.object(
                PersonalityModel, "get_for_user", return_value=mock_personality
            ),
            patch.object(PersonalityMessageModel, "create", return_value=mock_message),
            patch(
                "neuron_server.controllers.personality_message_controller.secure_pubsub"
            ) as mock_pubsub,
        ):
            mock_pubsub.publish_personality_room_message = AsyncMock()
            async with app.test_client() as client:
                response = await client.post(
                    f"/api/personality-messages/{personality_id}",
                    headers={"Authorization": TEST_JWT_TOKEN},
                    json={"content": "Test message"},
                )

                assert response.status_code == 200
                data = await response.get_json()
                assert "personality_message" in data
                mock_pubsub.publish_personality_room_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_personality_message_success(
        self, app, mock_decode_token, mock_personality, mock_message
    ):
        """Test successfully updating a personality message."""
        personality_id = uuid4()
        message_id = uuid4()
        mock_message.personality_id = personality_id
        mock_message.user_id = "test_user_id"

        with (
            patch.object(
                PersonalityModel, "get_for_user", return_value=mock_personality
            ),
            patch.object(PersonalityMessageModel, "get", return_value=mock_message),
            patch.object(PersonalityMessageModel, "update", return_value=mock_message),
            patch(
                "neuron_server.controllers.personality_message_controller.secure_pubsub"
            ) as mock_pubsub,
        ):
            mock_pubsub.publish_personality_room_message = AsyncMock()
            async with app.test_client() as client:
                response = await client.put(
                    f"/api/personality-messages/{personality_id}/messages/{message_id}",
                    headers={"Authorization": TEST_JWT_TOKEN},
                    json={"content": "Updated message"},
                )

                assert response.status_code == 200
                data = await response.get_json()
                assert "personality_message" in data
                mock_pubsub.publish_personality_room_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_personality_message_forbidden(
        self, app, mock_decode_token, mock_personality, mock_message
    ):
        """Test updating message owned by different user."""
        personality_id = uuid4()
        message_id = uuid4()
        mock_message.personality_id = personality_id
        mock_message.user_id = "different_user_id"  # Different user

        with (
            patch.object(
                PersonalityModel, "get_for_user", return_value=mock_personality
            ),
            patch.object(PersonalityMessageModel, "get", return_value=mock_message),
        ):
            async with app.test_client() as client:
                response = await client.put(
                    f"/api/personality-messages/{personality_id}/messages/{message_id}",
                    headers={"Authorization": TEST_JWT_TOKEN},
                    json={"content": "Updated message"},
                )

                assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_personality_message_success_owner(
        self, app, mock_decode_token, mock_personality, mock_message
    ):
        """Test successfully deleting own message."""
        personality_id = uuid4()
        message_id = uuid4()
        mock_message.personality_id = personality_id
        mock_message.user_id = "test_user_id"

        with (
            patch.object(PersonalityModel, "has_admin_access", return_value=False),
            patch.object(
                PersonalityModel, "get_for_user", return_value=mock_personality
            ),
            patch.object(PersonalityMessageModel, "get", return_value=mock_message),
            patch.object(PersonalityMessageModel, "delete") as mock_delete,
            patch(
                "neuron_server.controllers.personality_message_controller.secure_pubsub"
            ) as mock_pubsub,
        ):
            mock_pubsub.publish_personality_room_message = AsyncMock()
            async with app.test_client() as client:
                response = await client.delete(
                    f"/api/personality-messages/{personality_id}/messages/{message_id}",
                    headers={"Authorization": TEST_JWT_TOKEN},
                )

                assert response.status_code == 204
                mock_delete.assert_called_once_with(message_id)
                mock_pubsub.publish_personality_room_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_personality_message_success_admin(
        self, app, mock_decode_token, mock_message
    ):
        """Test successfully deleting message as admin."""
        personality_id = uuid4()
        message_id = uuid4()
        mock_message.personality_id = personality_id
        mock_message.user_id = (
            "different_user_id"  # Different user but admin can delete
        )

        with (
            patch.object(PersonalityModel, "has_admin_access", return_value=True),
            patch.object(PersonalityMessageModel, "get", return_value=mock_message),
            patch.object(PersonalityMessageModel, "delete") as mock_delete,
            patch(
                "neuron_server.controllers.personality_message_controller.secure_pubsub"
            ) as mock_pubsub,
        ):
            mock_pubsub.publish_personality_room_message = AsyncMock()
            async with app.test_client() as client:
                response = await client.delete(
                    f"/api/personality-messages/{personality_id}/messages/{message_id}",
                    headers={"Authorization": TEST_JWT_TOKEN},
                )

                assert response.status_code == 204
                mock_delete.assert_called_once_with(message_id)
                mock_pubsub.publish_personality_room_message.assert_called_once()


class TestPersonalityRoomEvents:
    """Tests for personality room WebSocket event handlers."""

    @pytest.mark.asyncio
    async def test_join_personality_room_success(self, mock_websocket_session):
        """Test successfully joining a personality room."""
        personality_id = uuid4()
        event = JoinPersonalityRoom(
            type="JoinPersonalityRoom", personality_id=personality_id
        )

        with patch(
            "neuron_server.controllers.personality_message_controller.permission_service"
        ) as mock_permission:
            mock_permission.user_has_personality_access = AsyncMock(return_value=True)

            with patch(
                "neuron_server.controllers.personality_message_controller.room_manager"
            ) as mock_room_manager:
                mock_room_manager.join_personality_room = AsyncMock(return_value=True)
                mock_room_manager.get_personality_room_members = AsyncMock(
                    return_value=["test_user_id", "other_user"]
                )

                with patch(
                    "neuron_server.controllers.personality_message_controller.secure_pubsub"
                ) as mock_pubsub:
                    mock_pubsub.publish_to_user = AsyncMock()
                    mock_pubsub.publish_to_users = AsyncMock()

                    await ajoin_personality_room(event, mock_websocket_session)

                    mock_room_manager.join_personality_room.assert_called_once_with(
                        personality_id, "test_user_id", "test_user"
                    )
                    # Should publish join event to user and user joined event to others
                    assert mock_pubsub.publish_to_user.call_count == 1
                    assert mock_pubsub.publish_to_users.call_count == 1

    @pytest.mark.asyncio
    async def test_join_personality_room_no_access(self, mock_websocket_session):
        """Test joining personality room without permission."""
        personality_id = uuid4()
        event = JoinPersonalityRoom(
            type="JoinPersonalityRoom", personality_id=personality_id
        )

        with patch(
            "neuron_server.controllers.personality_message_controller.permission_service"
        ) as mock_permission:
            mock_permission.user_has_personality_access = AsyncMock(return_value=False)

            with patch(
                "neuron_server.controllers.personality_message_controller.room_manager"
            ) as mock_room_manager:
                mock_room_manager.join_personality_room = AsyncMock()

                await ajoin_personality_room(event, mock_websocket_session)

                # Should not attempt to join room
                mock_room_manager.join_personality_room.assert_not_called()

    @pytest.mark.asyncio
    async def test_join_personality_room_no_session(self):
        """Test joining personality room without session."""
        personality_id = uuid4()
        event = JoinPersonalityRoom(
            type="JoinPersonalityRoom", personality_id=personality_id
        )

        with patch(
            "neuron_server.controllers.personality_message_controller.logger"
        ) as mock_logger:
            await ajoin_personality_room(event, None)

            mock_logger.error.assert_called_once_with(
                "JoinPersonalityRoom event received without session context"
            )

    @pytest.mark.asyncio
    async def test_leave_personality_room_success(self, mock_websocket_session):
        """Test successfully leaving a personality room."""
        personality_id = uuid4()
        event = LeavePersonalityRoom(
            type="LeavePersonalityRoom", personality_id=personality_id
        )

        with patch(
            "neuron_server.controllers.personality_message_controller.room_manager"
        ) as mock_room_manager:
            mock_room_manager.get_personality_room_members = AsyncMock(
                return_value=["test_user_id", "other_user"]
            )
            mock_room_manager.leave_personality_room = AsyncMock(return_value=True)

            with patch(
                "neuron_server.controllers.personality_message_controller.secure_pubsub"
            ) as mock_pubsub:
                mock_pubsub.publish_to_user = AsyncMock()
                mock_pubsub.publish_to_users = AsyncMock()

                await aleave_personality_room(event, mock_websocket_session)

                mock_room_manager.leave_personality_room.assert_called_once_with(
                    personality_id, "test_user_id"
                )
                # Should publish leave event to user and user left event to others
                assert mock_pubsub.publish_to_user.call_count == 1
                assert mock_pubsub.publish_to_users.call_count == 1

    @pytest.mark.asyncio
    async def test_leave_personality_room_no_session(self):
        """Test leaving personality room without session."""
        personality_id = uuid4()
        event = LeavePersonalityRoom(
            type="LeavePersonalityRoom", personality_id=personality_id
        )

        with patch(
            "neuron_server.controllers.personality_message_controller.logger"
        ) as mock_logger:
            await aleave_personality_room(event, None)

            mock_logger.error.assert_called_once_with(
                "LeavePersonalityRoom event received without session context"
            )

    @pytest.mark.asyncio
    async def test_cleanup_user_personality_rooms(self, mock_websocket_session):
        """Test cleaning up user from personality rooms on disconnect."""
        room_info = [
            {"room_type": "personality", "room_id": str(uuid4())},
            {"room_type": "thread", "room_id": str(uuid4())},  # Should be ignored
            {"room_type": "personality", "room_id": str(uuid4())},
        ]

        with patch(
            "neuron_server.controllers.personality_message_controller.room_manager"
        ) as mock_room_manager:
            mock_room_manager.get_user_rooms = AsyncMock(return_value=room_info)
            mock_room_manager.get_room_members = AsyncMock(
                return_value=["test_user_id", "other_user"]
            )
            mock_room_manager.leave_room = AsyncMock(return_value=True)
            mock_room_manager.cleanup_user_from_all_rooms = AsyncMock()

            with patch(
                "neuron_server.controllers.personality_message_controller.secure_pubsub"
            ) as mock_pubsub:
                mock_pubsub.publish_to_users = AsyncMock()

                await cleanup_user_personality_rooms(mock_websocket_session)

                # Should only process personality rooms (2 out of 3)
                assert mock_room_manager.leave_room.call_count == 2
                assert mock_pubsub.publish_to_users.call_count == 2
                mock_room_manager.cleanup_user_from_all_rooms.assert_called_once_with(
                    "test_user_id"
                )
