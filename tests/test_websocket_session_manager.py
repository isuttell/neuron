"""Tests for WebSocket session manager with Redis backend."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from quart import Websocket

from neuron_server.controllers.auth import TokenPayload
from neuron_server.redis_session_store import SessionData
from neuron_server.websocket_session_manager import WebSocketSession, WebSocketSessionManager


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection."""
    websocket = MagicMock(spec=Websocket)
    websocket.send = AsyncMock()
    return websocket


@pytest.fixture
def sample_token():
    """Sample token payload for testing."""
    return TokenPayload(
        roles=["user"],
        user_id="user123",
        email="test@example.com",
        nickname="testuser",
        picture="https://example.com/avatar.jpg",
        permissions=["read:messages", "write:messages"]
    )


@pytest.fixture
def session_manager():
    """Create WebSocketSessionManager for testing."""
    return WebSocketSessionManager()


@pytest.fixture
def mock_redis_session_store():
    """Mock Redis session store."""
    store = MagicMock()
    store.add_session = AsyncMock()
    store.remove_session = AsyncMock()
    store.get_session = AsyncMock()
    store.get_user_sessions = AsyncMock()
    store.get_active_users = AsyncMock()
    store.update_session_activity = AsyncMock()
    store.cleanup_expired_sessions = AsyncMock()
    store.get_session_count = AsyncMock()
    store.get_user_count = AsyncMock()
    return store


class TestWebSocketSession:
    """Test WebSocketSession dataclass."""

    def test_websocket_session_creation(self, mock_websocket, sample_token):
        """Test creating WebSocketSession."""
        session = WebSocketSession(
            websocket=mock_websocket,
            user_id="user123",
            nickname="testuser",
            session_id="session123",
            token=sample_token
        )

        assert session.websocket == mock_websocket
        assert session.user_id == "user123"
        assert session.nickname == "testuser"
        assert session.session_id == "session123"
        assert session.token == sample_token


class TestWebSocketSessionManager:
    """Test WebSocketSessionManager functionality."""

    @pytest.mark.asyncio
    async def test_add_session(self, session_manager, mock_websocket, sample_token, mock_redis_session_store):
        """Test adding a session."""
        # Mock Redis store response
        session_data = SessionData(
            user_id="user123",
            nickname="testuser",
            session_id="session123",
            token_data=sample_token.model_dump()
        )
        mock_redis_session_store.add_session.return_value = session_data

        with patch("neuron_server.websocket_session_manager.redis_session_store", mock_redis_session_store):
            session = await session_manager.add_session(mock_websocket, sample_token, "session123")

        # Verify session object
        assert isinstance(session, WebSocketSession)
        assert session.websocket == mock_websocket
        assert session.user_id == "user123"
        assert session.nickname == "testuser"
        assert session.session_id == "session123"

        # Verify Redis store was called
        mock_redis_session_store.add_session.assert_called_once_with(
            session_id="session123",
            user_id="user123",
            nickname="testuser",
            token=sample_token
        )

        # Verify websocket is stored in memory
        assert session_manager._websockets["session123"] == mock_websocket

    @pytest.mark.asyncio
    async def test_remove_session(self, session_manager, mock_websocket, sample_token, mock_redis_session_store):
        """Test removing a session."""
        # Add session first
        session_manager._websockets["session123"] = mock_websocket

        # Mock Redis store response
        session_data = SessionData(
            user_id="user123",
            nickname="testuser",
            session_id="session123",
            token_data=sample_token.model_dump()
        )
        mock_redis_session_store.remove_session.return_value = session_data

        with patch("neuron_server.websocket_session_manager.redis_session_store", mock_redis_session_store):
            await session_manager.remove_session("session123")

        # Verify Redis store was called
        mock_redis_session_store.remove_session.assert_called_once_with("session123")

        # Verify websocket is removed from memory
        assert "session123" not in session_manager._websockets

    @pytest.mark.asyncio
    async def test_get_session(self, session_manager, mock_websocket, sample_token, mock_redis_session_store):
        """Test getting a session."""
        # Add websocket to memory
        session_manager._websockets["session123"] = mock_websocket

        # Mock Redis store response
        session_data = SessionData(
            user_id="user123",
            nickname="testuser",
            session_id="session123",
            token_data=sample_token.model_dump()
        )
        mock_redis_session_store.get_session.return_value = session_data
        mock_redis_session_store.update_session_activity.return_value = True

        with patch("neuron_server.websocket_session_manager.redis_session_store", mock_redis_session_store):
            session = await session_manager.get_session("session123")

        # Verify session object
        assert session is not None
        assert session.websocket == mock_websocket
        assert session.user_id == "user123"
        assert session.session_id == "session123"

        # Verify Redis calls
        mock_redis_session_store.get_session.assert_called_once_with("session123")
        mock_redis_session_store.update_session_activity.assert_called_once_with("session123")

    @pytest.mark.asyncio
    async def test_get_session_not_in_redis(self, session_manager, mock_redis_session_store):
        """Test getting a session that doesn't exist in Redis."""
        mock_redis_session_store.get_session.return_value = None

        with patch("neuron_server.websocket_session_manager.redis_session_store", mock_redis_session_store):
            session = await session_manager.get_session("nonexistent")

        assert session is None

    @pytest.mark.asyncio
    async def test_get_session_websocket_not_in_memory(self, session_manager, sample_token, mock_redis_session_store):
        """Test getting a session when websocket is not in memory."""
        # Mock Redis store response but no websocket in memory
        session_data = SessionData(
            user_id="user123",
            nickname="testuser",
            session_id="session123",
            token_data=sample_token.model_dump()
        )
        mock_redis_session_store.get_session.return_value = session_data

        with patch("neuron_server.websocket_session_manager.redis_session_store", mock_redis_session_store):
            session = await session_manager.get_session("session123")

        # Should return None and clean up Redis
        assert session is None
        mock_redis_session_store.remove_session.assert_called_once_with("session123")

    @pytest.mark.asyncio
    async def test_get_user_sessions(self, session_manager, mock_websocket, sample_token, mock_redis_session_store):
        """Test getting all sessions for a user."""
        # Add websockets to memory
        mock_websocket2 = MagicMock(spec=Websocket)
        session_manager._websockets["session123"] = mock_websocket
        session_manager._websockets["session456"] = mock_websocket2

        # Mock Redis store response
        session_data1 = SessionData(
            user_id="user123",
            nickname="testuser",
            session_id="session123",
            token_data=sample_token.model_dump()
        )
        session_data2 = SessionData(
            user_id="user123",
            nickname="testuser",
            session_id="session456",
            token_data=sample_token.model_dump()
        )
        mock_redis_session_store.get_user_sessions.return_value = [session_data1, session_data2]

        with patch("neuron_server.websocket_session_manager.redis_session_store", mock_redis_session_store):
            sessions = await session_manager.get_user_sessions("user123")

        # Verify results
        assert len(sessions) == 2
        session_ids = {s.session_id for s in sessions}
        assert "session123" in session_ids
        assert "session456" in session_ids

        # Verify Redis call
        mock_redis_session_store.get_user_sessions.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_get_user_sessions_with_stale_session(self, session_manager, mock_websocket, sample_token, mock_redis_session_store):
        """Test getting user sessions when some websockets are not in memory."""
        # Add only one websocket to memory
        session_manager._websockets["session123"] = mock_websocket

        # Mock Redis store response with two sessions
        session_data1 = SessionData(
            user_id="user123",
            nickname="testuser",
            session_id="session123",
            token_data=sample_token.model_dump()
        )
        session_data2 = SessionData(
            user_id="user123",
            nickname="testuser",
            session_id="session456",  # This websocket is not in memory
            token_data=sample_token.model_dump()
        )
        mock_redis_session_store.get_user_sessions.return_value = [session_data1, session_data2]

        with patch("neuron_server.websocket_session_manager.redis_session_store", mock_redis_session_store):
            sessions = await session_manager.get_user_sessions("user123")

        # Should only return the session with websocket in memory
        assert len(sessions) == 1
        assert sessions[0].session_id == "session123"

        # Should clean up the stale session
        mock_redis_session_store.remove_session.assert_called_once_with("session456")

    @pytest.mark.asyncio
    async def test_send_to_user(self, session_manager, mock_websocket, sample_token, mock_redis_session_store):
        """Test sending message to user."""
        # Add websocket to memory
        session_manager._websockets["session123"] = mock_websocket

        # Mock Redis store response
        session_data = SessionData(
            user_id="user123",
            nickname="testuser",
            session_id="session123",
            token_data=sample_token.model_dump()
        )
        mock_redis_session_store.get_user_sessions.return_value = [session_data]
        mock_redis_session_store.update_session_activity.return_value = True

        with patch("neuron_server.websocket_session_manager.redis_session_store", mock_redis_session_store):
            await session_manager.send_to_user("user123", "test message")

        # Verify message was sent
        mock_websocket.send.assert_called_once_with("test message")

        # Verify session activity was updated
        mock_redis_session_store.update_session_activity.assert_called_once_with("session123")

    @pytest.mark.asyncio
    async def test_send_to_user_websocket_error(self, session_manager, mock_websocket, sample_token, mock_redis_session_store):
        """Test sending message when websocket fails."""
        # Add websocket to memory
        session_manager._websockets["session123"] = mock_websocket

        # Mock websocket send to raise exception
        mock_websocket.send.side_effect = Exception("Connection closed")

        # Mock Redis store response
        session_data = SessionData(
            user_id="user123",
            nickname="testuser",
            session_id="session123",
            token_data=sample_token.model_dump()
        )
        mock_redis_session_store.get_user_sessions.return_value = [session_data]
        mock_redis_session_store.remove_session.return_value = session_data

        with patch("neuron_server.websocket_session_manager.redis_session_store", mock_redis_session_store):
            await session_manager.send_to_user("user123", "test message")

        # Verify session was removed due to error
        mock_redis_session_store.remove_session.assert_called_once_with("session123")
        assert "session123" not in session_manager._websockets

    @pytest.mark.asyncio
    async def test_get_active_users(self, session_manager, mock_redis_session_store):
        """Test getting active users."""
        mock_redis_session_store.get_active_users.return_value = {"user123", "user456"}

        with patch("neuron_server.websocket_session_manager.redis_session_store", mock_redis_session_store):
            active_users = await session_manager.get_active_users()

        assert "user123" in active_users
        assert "user456" in active_users
        assert len(active_users) == 2

    @pytest.mark.asyncio
    async def test_get_session_count(self, session_manager, mock_redis_session_store):
        """Test getting session count."""
        mock_redis_session_store.get_session_count.return_value = 5

        with patch("neuron_server.websocket_session_manager.redis_session_store", mock_redis_session_store):
            count = await session_manager.get_session_count()

        assert count == 5

    @pytest.mark.asyncio
    async def test_get_user_count(self, session_manager, mock_redis_session_store):
        """Test getting user count."""
        mock_redis_session_store.get_user_count.return_value = 3

        with patch("neuron_server.websocket_session_manager.redis_session_store", mock_redis_session_store):
            count = await session_manager.get_user_count()

        assert count == 3

    @pytest.mark.asyncio
    async def test_cleanup_sessions(self, session_manager, mock_redis_session_store):
        """Test session cleanup."""
        # Add some websockets to memory
        session_manager._websockets["session123"] = MagicMock()
        session_manager._websockets["session456"] = MagicMock()
        session_manager._websockets["session789"] = MagicMock()

        # Mock Redis cleanup
        mock_redis_session_store.cleanup_expired_sessions.return_value = 2

        # Mock get_session to return None for session789 (orphaned)
        def mock_get_session(session_id):
            if session_id == "session789":
                return None
            return SessionData(
                user_id="user123",
                nickname="testuser",
                session_id=session_id,
                token_data={}
            )

        mock_redis_session_store.get_session.side_effect = mock_get_session

        with patch("neuron_server.websocket_session_manager.redis_session_store", mock_redis_session_store):
            cleanup_count = await session_manager.cleanup_sessions()

        # Should have cleaned up 2 Redis sessions + 1 orphaned websocket = 3 total
        assert cleanup_count == 3

        # Verify orphaned websocket was removed
        assert "session789" not in session_manager._websockets
        assert "session123" in session_manager._websockets
        assert "session456" in session_manager._websockets

    @pytest.mark.asyncio
    async def test_broadcast_to_users(self, session_manager):
        """Test broadcasting to multiple users."""
        with patch.object(session_manager, "send_to_user", new=AsyncMock()) as mock_send:
            await session_manager.broadcast_to_users(["user123", "user456"], "broadcast message")

        # Verify send_to_user was called for each user
        assert mock_send.call_count == 2
        mock_send.assert_any_call("user123", "broadcast message")
        mock_send.assert_any_call("user456", "broadcast message")


class TestWebSocketSessionManagerIntegration:
    """Integration tests for session manager."""

    @pytest.mark.asyncio
    async def test_session_lifecycle(self, session_manager, mock_websocket, sample_token, mock_redis_session_store):
        """Test complete session lifecycle."""
        # Mock Redis store responses
        session_data = SessionData(
            user_id="user123",
            nickname="testuser",
            session_id="session123",
            token_data=sample_token.model_dump()
        )
        mock_redis_session_store.add_session.return_value = session_data
        mock_redis_session_store.get_session.return_value = session_data
        mock_redis_session_store.get_user_sessions.return_value = [session_data]  # Add this for send_to_user
        mock_redis_session_store.remove_session.return_value = session_data
        mock_redis_session_store.update_session_activity.return_value = True

        with patch("neuron_server.websocket_session_manager.redis_session_store", mock_redis_session_store):
            # Add session
            session = await session_manager.add_session(mock_websocket, sample_token, "session123")
            assert session.session_id == "session123"

            # Get session
            retrieved_session = await session_manager.get_session("session123")
            assert retrieved_session is not None
            assert retrieved_session.session_id == "session123"

            # Send message
            await session_manager.send_to_user("user123", "test")
            mock_websocket.send.assert_called_with("test")

            # Remove session
            await session_manager.remove_session("session123")
            assert "session123" not in session_manager._websockets


if __name__ == "__main__":
    pytest.main([__file__])
