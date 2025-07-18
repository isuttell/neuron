"""Tests for Redis session store functionality."""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import redis.asyncio as redis

from neuron_server.controllers.auth import TokenPayload
from neuron_server.redis_session_store import RedisSessionStore, SessionData


class MockAsyncIterator:
    """Mock async iterator for scan_iter."""
    def __init__(self, items):
        self.items = items
        self.index = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self.index >= len(self.items):
            raise StopAsyncIteration
        item = self.items[self.index]
        self.index += 1
        return item


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    mock_client = MagicMock()

    # Mock async methods
    mock_client.hset = AsyncMock()
    mock_client.hgetall = AsyncMock()
    mock_client.expire = AsyncMock()
    mock_client.delete = AsyncMock()
    mock_client.sadd = AsyncMock()
    mock_client.srem = AsyncMock()
    mock_client.smembers = AsyncMock()
    mock_client.scard = AsyncMock()
    mock_client.exists = AsyncMock()

    # Mock scan_iter to return an async iterator
    def mock_scan_iter(match="*"):
        if match == "session:*":
            return MockAsyncIterator([b"session:session123", b"session:session456", b"session:session789"])
        elif match == "user_sessions:*":
            return MockAsyncIterator([b"user_sessions:user123", b"user_sessions:user456"])
        return MockAsyncIterator([])

    mock_client.scan_iter = MagicMock(side_effect=mock_scan_iter)

    return mock_client


@pytest.fixture
def session_store(mock_redis):
    """Create RedisSessionStore with mocked Redis client."""
    return RedisSessionStore(mock_redis, session_ttl=3600)


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


class TestSessionData:
    """Test SessionData serialization and deserialization."""

    def test_session_data_creation(self, sample_token):
        """Test creating SessionData."""
        session_data = SessionData(
            user_id="user123",
            nickname="testuser",
            session_id="session123",
            token_data=sample_token.model_dump()
        )

        assert session_data.user_id == "user123"
        assert session_data.nickname == "testuser"
        assert session_data.session_id == "session123"
        assert session_data.created_at is not None
        assert session_data.last_active is not None

    def test_session_data_to_dict(self, sample_token):
        """Test converting SessionData to dictionary."""
        session_data = SessionData(
            user_id="user123",
            nickname="testuser",
            session_id="session123",
            token_data=sample_token.model_dump(),
            created_at=1234567890.0,
            last_active=1234567900.0
        )

        data_dict = session_data.to_dict()

        assert data_dict["user_id"] == "user123"
        assert data_dict["nickname"] == "testuser"
        assert data_dict["session_id"] == "session123"
        assert json.loads(data_dict["token_data"]) == sample_token.model_dump()
        assert data_dict["created_at"] == 1234567890.0
        assert data_dict["last_active"] == 1234567900.0

    def test_session_data_from_dict(self, sample_token):
        """Test creating SessionData from dictionary."""
        data_dict = {
            "user_id": "user123",
            "nickname": "testuser",
            "session_id": "session123",
            "token_data": json.dumps(sample_token.model_dump()),
            "created_at": "1234567890.0",
            "last_active": "1234567900.0"
        }

        session_data = SessionData.from_dict(data_dict)

        assert session_data.user_id == "user123"
        assert session_data.nickname == "testuser"
        assert session_data.session_id == "session123"
        assert session_data.token_data == sample_token.model_dump()
        assert session_data.created_at == 1234567890.0
        assert session_data.last_active == 1234567900.0

    def test_session_data_to_token_payload(self, sample_token):
        """Test converting SessionData to TokenPayload."""
        session_data = SessionData(
            user_id="user123",
            nickname="testuser",
            session_id="session123",
            token_data=sample_token.model_dump()
        )

        token_payload = session_data.to_token_payload()

        assert isinstance(token_payload, TokenPayload)
        assert token_payload.user_id == sample_token.user_id
        assert token_payload.nickname == sample_token.nickname


class TestRedisSessionStore:
    """Test RedisSessionStore functionality."""

    @pytest.mark.asyncio
    async def test_add_session(self, session_store, mock_redis, sample_token):
        """Test adding a session."""
        session_data = await session_store.add_session(
            session_id="session123",
            user_id="user123",
            nickname="testuser",
            token=sample_token
        )

        # Verify session data
        assert session_data.user_id == "user123"
        assert session_data.nickname == "testuser"
        assert session_data.session_id == "session123"

        # Verify Redis calls
        mock_redis.hset.assert_called_once()
        mock_redis.expire.assert_called()
        mock_redis.sadd.assert_called_once()

        # Check the session key and user sessions key
        hset_call = mock_redis.hset.call_args
        assert hset_call[0][0] == "session:session123"

        sadd_call = mock_redis.sadd.call_args
        assert sadd_call[0][0] == "user_sessions:user123"
        assert sadd_call[0][1] == "session123"

    @pytest.mark.asyncio
    async def test_remove_session(self, session_store, mock_redis, sample_token):
        """Test removing a session."""
        # Mock existing session data
        session_dict = {
            b"user_id": b"user123",
            b"nickname": b"testuser",
            b"session_id": b"session123",
            b"token_data": json.dumps(sample_token.model_dump()).encode(),
            b"created_at": b"1234567890.0",
            b"last_active": b"1234567900.0"
        }
        mock_redis.hgetall.return_value = session_dict
        mock_redis.scard.return_value = 0  # No other sessions for user

        session_data = await session_store.remove_session("session123")

        # Verify returned session data
        assert session_data is not None
        assert session_data.user_id == "user123"
        assert session_data.session_id == "session123"

        # Verify Redis calls
        mock_redis.hgetall.assert_called_with("session:session123")
        mock_redis.delete.assert_called()
        mock_redis.srem.assert_called_with("user_sessions:user123", "session123")

    @pytest.mark.asyncio
    async def test_get_session(self, session_store, mock_redis, sample_token):
        """Test getting a session."""
        # Mock session data
        session_dict = {
            b"user_id": b"user123",
            b"nickname": b"testuser",
            b"session_id": b"session123",
            b"token_data": json.dumps(sample_token.model_dump()).encode(),
            b"created_at": b"1234567890.0",
            b"last_active": b"1234567900.0"
        }
        mock_redis.hgetall.return_value = session_dict

        session_data = await session_store.get_session("session123")

        # Verify session data
        assert session_data is not None
        assert session_data.user_id == "user123"
        assert session_data.nickname == "testuser"
        assert session_data.session_id == "session123"

        # Verify Redis call
        mock_redis.hgetall.assert_called_with("session:session123")

    @pytest.mark.asyncio
    async def test_get_session_not_found(self, session_store, mock_redis):
        """Test getting a non-existent session."""
        mock_redis.hgetall.return_value = {}

        session_data = await session_store.get_session("nonexistent")

        assert session_data is None

    @pytest.mark.asyncio
    async def test_get_user_sessions(self, session_store, mock_redis, sample_token):
        """Test getting all sessions for a user."""
        # Mock user session IDs
        mock_redis.smembers.return_value = {b"session123", b"session456"}

        # Mock session data for each session
        session_dict1 = {
            b"user_id": b"user123",
            b"nickname": b"testuser",
            b"session_id": b"session123",
            b"token_data": json.dumps(sample_token.model_dump()).encode(),
            b"created_at": b"1234567890.0",
            b"last_active": b"1234567900.0"
        }
        session_dict2 = {
            b"user_id": b"user123",
            b"nickname": b"testuser",
            b"session_id": b"session456",
            b"token_data": json.dumps(sample_token.model_dump()).encode(),
            b"created_at": b"1234567890.0",
            b"last_active": b"1234567900.0"
        }

        # Mock hgetall to return different data based on key
        def mock_hgetall(key):
            if key == "session:session123":
                return session_dict1
            elif key == "session:session456":
                return session_dict2
            return {}

        mock_redis.hgetall.side_effect = mock_hgetall

        sessions = await session_store.get_user_sessions("user123")

        # Verify results
        assert len(sessions) == 2
        session_ids = {s.session_id for s in sessions}
        assert "session123" in session_ids
        assert "session456" in session_ids

    @pytest.mark.asyncio
    async def test_update_session_activity(self, session_store, mock_redis):
        """Test updating session activity."""
        mock_redis.exists.return_value = 1  # Session exists
        mock_redis.hgetall.return_value = {
            b"user_id": b"user123",
            b"nickname": b"testuser",
            b"session_id": b"session123",
            b"token_data": b'{"user_id": "user123"}',
            b"created_at": b"1234567890.0",
            b"last_active": b"1234567900.0"
        }

        with patch("time.time", return_value=1234567950.0):
            result = await session_store.update_session_activity("session123")

        assert result is True

        # Verify Redis calls
        mock_redis.exists.assert_called_with("session:session123")
        mock_redis.hset.assert_called()
        mock_redis.expire.assert_called()

        # Check that last_active was updated
        hset_call = mock_redis.hset.call_args
        assert hset_call[0][1] == "last_active"
        assert hset_call[0][2] == 1234567950.0

    @pytest.mark.asyncio
    async def test_update_session_activity_not_found(self, session_store, mock_redis):
        """Test updating activity for non-existent session."""
        mock_redis.exists.return_value = 0  # Session doesn't exist

        result = await session_store.update_session_activity("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_expired_sessions(self, session_store, mock_redis):
        """Test cleaning up expired sessions."""

        # Mock session IDs for each user
        def mock_smembers(key):
            if key == "user_sessions:user123":
                return {b"session123", b"session456"}
            elif key == "user_sessions:user456":
                return {b"session789"}
            return set()

        mock_redis.smembers.side_effect = mock_smembers

        # Mock session existence - session456 and session789 don't exist
        def mock_exists(key):
            return 1 if key == "session:session123" else 0

        mock_redis.exists.side_effect = mock_exists

        cleanup_count = await session_store.cleanup_expired_sessions()

        # Should have cleaned up 2 sessions (session456 and session789)
        assert cleanup_count == 2

        # Verify Redis calls
        assert mock_redis.smembers.call_count == 2
        assert mock_redis.exists.call_count == 3

    @pytest.mark.asyncio
    async def test_get_active_users(self, session_store, mock_redis):
        """Test getting active users."""
        mock_redis.scard.return_value = 1  # All users have at least one session

        active_users = await session_store.get_active_users()

        assert "user123" in active_users
        assert "user456" in active_users
        assert len(active_users) == 2

    @pytest.mark.asyncio
    async def test_get_session_count(self, session_store, mock_redis):
        """Test getting total session count."""
        count = await session_store.get_session_count()

        assert count == 3

    @pytest.mark.asyncio
    async def test_get_user_count(self, session_store, mock_redis):
        """Test getting total user count."""
        with patch.object(session_store, "get_active_users") as mock_get_users:
            mock_get_users.return_value = {"user123", "user456", "user789"}

            count = await session_store.get_user_count()

            assert count == 3


class TestRedisSessionStoreIntegration:
    """Integration tests with real Redis operations (mocked)."""

    @pytest.mark.asyncio
    async def test_session_lifecycle(self, session_store, mock_redis, sample_token):
        """Test complete session lifecycle: add, get, update, remove."""
        # Add session
        session_data = await session_store.add_session(
            session_id="session123",
            user_id="user123",
            nickname="testuser",
            token=sample_token
        )

        assert session_data.session_id == "session123"

        # Mock get session
        session_dict = {
            b"user_id": b"user123",
            b"nickname": b"testuser",
            b"session_id": b"session123",
            b"token_data": json.dumps(sample_token.model_dump()).encode(),
            b"created_at": str(session_data.created_at).encode(),
            b"last_active": str(session_data.last_active).encode()
        }
        mock_redis.hgetall.return_value = session_dict

        # Get session
        retrieved_session = await session_store.get_session("session123")
        assert retrieved_session is not None
        assert retrieved_session.session_id == "session123"

        # Update activity
        mock_redis.exists.return_value = 1
        updated = await session_store.update_session_activity("session123")
        assert updated is True

        # Remove session
        mock_redis.scard.return_value = 0
        removed_session = await session_store.remove_session("session123")
        assert removed_session is not None
        assert removed_session.session_id == "session123"


if __name__ == "__main__":
    pytest.main([__file__])
