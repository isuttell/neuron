import asyncio
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from neuron_server.room_manager import RoomManager


@pytest.fixture
def mock_redis_client():
    """Mock Redis client."""
    return AsyncMock()


@pytest.fixture
def room_manager(mock_redis_client):
    """Room manager instance with mocked Redis client."""
    return RoomManager(mock_redis_client, room_ttl=3600)


class TestRoomManager:
    """Tests for the Redis-based room manager."""

    def test_room_keys_generation(self, room_manager):
        """Test Redis key generation methods."""
        assert (
            room_manager._room_members_key("personality_room", "123")
            == "room:personality_room:123:members"
        )
        assert (
            room_manager._room_metadata_key("personality_room", "123")
            == "room:personality_room:123:metadata"
        )
        assert room_manager._user_rooms_key("user123") == "user:user123:rooms"

    @pytest.mark.asyncio
    async def test_join_room_new_user(self, room_manager, mock_redis_client):
        """Test joining a room as a new user."""
        mock_redis_client.sismember.return_value = False  # User not already in room
        mock_redis_client.sadd.return_value = 1  # User was added (new member)
        mock_redis_client.expire.return_value = True
        mock_redis_client.hset.return_value = 1

        result = await room_manager.join_room(
            "personality_room", "room123", "user456", "TestUser"
        )

        assert result is True
        mock_redis_client.sismember.assert_called()
        mock_redis_client.sadd.assert_called()
        mock_redis_client.expire.assert_called()
        mock_redis_client.hset.assert_called()

    @pytest.mark.asyncio
    async def test_join_room_existing_user(self, room_manager, mock_redis_client):
        """Test joining a room as an existing user."""
        mock_redis_client.sismember.return_value = True  # User already in room
        mock_redis_client.expire.return_value = True

        result = await room_manager.join_room(
            "personality_room", "room123", "user456", "TestUser"
        )

        assert result is False
        mock_redis_client.sismember.assert_called()
        # Should not call sadd or hset for existing user
        mock_redis_client.sadd.assert_not_called()
        mock_redis_client.hset.assert_not_called()
        # Should refresh TTL even for existing user
        mock_redis_client.expire.assert_called()

    @pytest.mark.asyncio
    async def test_leave_room_existing_user(self, room_manager, mock_redis_client):
        """Test leaving a room as an existing user."""
        mock_redis_client.sismember.return_value = True  # User is in room
        mock_redis_client.srem.return_value = 1  # User was removed

        result = await room_manager.leave_room("personality_room", "room123", "user456")

        assert result is True
        # Should check membership and then remove from both sets
        mock_redis_client.sismember.assert_called()
        assert mock_redis_client.srem.call_count == 2

    @pytest.mark.asyncio
    async def test_leave_room_nonexistent_user(self, room_manager, mock_redis_client):
        """Test leaving a room as a non-existent user."""
        mock_redis_client.sismember.return_value = False  # User not in room

        result = await room_manager.leave_room("personality_room", "room123", "user456")

        assert result is False
        # Should check membership but not call srem
        mock_redis_client.sismember.assert_called()
        mock_redis_client.srem.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_room_members(self, room_manager, mock_redis_client):
        """Test getting room members."""
        mock_redis_client.smembers.return_value = {b"user1", b"user2", b"user3"}

        members = await room_manager.get_room_members("personality_room", "room123")

        # Set order doesn't matter, just check all members are present
        assert set(members) == {"user1", "user2", "user3"}
        mock_redis_client.smembers.assert_called_with(
            "room:personality_room:room123:members"
        )

    @pytest.mark.asyncio
    async def test_get_room_members_empty(self, room_manager, mock_redis_client):
        """Test getting members from empty room."""
        mock_redis_client.smembers.return_value = set()

        members = await room_manager.get_room_members("personality_room", "room123")

        assert members == []

    @pytest.mark.asyncio
    async def test_get_user_rooms(self, room_manager, mock_redis_client):
        """Test getting rooms a user is in."""
        mock_redis_client.smembers.return_value = {
            b"personality_room:room1",
            b"thread:room2",
        }

        rooms = await room_manager.get_user_rooms("user456")

        expected = [
            {"room_type": "personality_room", "room_id": "room1"},
            {"room_type": "thread", "room_id": "room2"},
        ]
        # Set doesn't guarantee order, so check both possible orders
        assert rooms == expected or rooms == list(reversed(expected))
        mock_redis_client.smembers.assert_called_with("user:user456:rooms")

    @pytest.mark.asyncio
    async def test_get_user_rooms_empty(self, room_manager, mock_redis_client):
        """Test getting rooms for user in no rooms."""
        mock_redis_client.smembers.return_value = set()

        rooms = await room_manager.get_user_rooms("user456")

        assert rooms == []

    @pytest.mark.asyncio
    async def test_join_personality_room(self, room_manager, mock_redis_client):
        """Test joining a personality room (convenience method)."""
        personality_id = uuid4()
        mock_redis_client.sismember.return_value = False  # User not in room
        mock_redis_client.sadd.return_value = 1
        mock_redis_client.expire.return_value = True
        mock_redis_client.hset.return_value = 1

        result = await room_manager.join_personality_room(
            personality_id, "user456", "TestUser"
        )

        assert result is True
        # Should call the underlying join_room logic
        mock_redis_client.sismember.assert_called()
        assert mock_redis_client.sadd.call_count == 2  # room members + user rooms

    @pytest.mark.asyncio
    async def test_leave_personality_room(self, room_manager, mock_redis_client):
        """Test leaving a personality room (convenience method)."""
        personality_id = uuid4()
        mock_redis_client.srem.return_value = 1

        result = await room_manager.leave_personality_room(personality_id, "user456")

        assert result is True
        # Should call leave_room with "personality" type and string ID
        assert mock_redis_client.srem.call_count == 2

    @pytest.mark.asyncio
    async def test_get_personality_room_members(self, room_manager, mock_redis_client):
        """Test getting personality room members (convenience method)."""
        personality_id = uuid4()
        mock_redis_client.smembers.return_value = {b"user1", b"user2"}

        members = await room_manager.get_personality_room_members(personality_id)

        # Set order doesn't matter, just check all members are present
        assert set(members) == {"user1", "user2"}
        mock_redis_client.smembers.assert_called_with(
            "room:personality_room:" + str(personality_id) + ":members"
        )

    @pytest.mark.asyncio
    async def test_update_room_activity(self, room_manager, mock_redis_client):
        """Test updating room activity timestamp."""
        mock_redis_client.hset.return_value = 1

        await room_manager.update_room_activity("personality_room", "room123")

        mock_redis_client.hset.assert_called_once()
        call_args = mock_redis_client.hset.call_args[0]
        assert call_args[0] == "room:personality_room:room123:metadata"
        assert call_args[1] == "last_activity"
        # Should set a timestamp (just check it's a number)
        assert isinstance(call_args[2], (int, float))

    @pytest.mark.asyncio
    async def test_cleanup_user_from_all_rooms(self, room_manager, mock_redis_client):
        """Test cleaning up user from all rooms."""
        # Mock user rooms
        mock_redis_client.smembers.return_value = {
            b"personality_room:room1",
            b"thread:room2",
        }
        mock_redis_client.srem.return_value = 1

        await room_manager.cleanup_user_from_all_rooms("user456")

        # Should get user rooms
        mock_redis_client.smembers.assert_called_with("user:user456:rooms")
        # Should remove user from each room and clean up user's room list
        assert mock_redis_client.srem.call_count >= 3  # 2 rooms + user rooms cleanup

    @pytest.mark.asyncio
    async def test_room_ttl_behavior(self, room_manager, mock_redis_client):
        """Test that room TTL is properly handled."""
        mock_redis_client.sismember.return_value = False
        mock_redis_client.sadd.return_value = 1
        mock_redis_client.expire.return_value = True
        mock_redis_client.hset.return_value = 1

        await room_manager.join_room(
            "personality_room", "room123", "user456", "TestUser"
        )

        # Should set TTL on room keys
        expire_calls = mock_redis_client.expire.call_args_list
        assert len(expire_calls) >= 3  # room members, metadata, user rooms
        # Check that TTL is set to the configured value (3600 in fixture)
        for call in expire_calls:
            assert call[0][1] == 3600

    @pytest.mark.asyncio
    async def test_concurrent_operations(self, room_manager, mock_redis_client):
        """Test that concurrent operations are handled safely with locks."""
        mock_redis_client.sismember.return_value = False  # Users not in room
        mock_redis_client.sadd.return_value = 1
        mock_redis_client.expire.return_value = True
        mock_redis_client.hset.return_value = 1

        # Simulate concurrent join operations
        tasks = [
            room_manager.join_room(
                "personality_room", "room123", f"user{i}", f"User{i}"
            )
            for i in range(5)
        ]

        results = await asyncio.gather(*tasks)

        # All operations should complete successfully
        assert all(result is True for result in results)
        assert mock_redis_client.sadd.call_count == 10  # 5 users × 2 calls each

    @pytest.mark.asyncio
    async def test_room_ttl_setting(self, room_manager, mock_redis_client):
        """Test that room TTL is properly set."""
        mock_redis_client.sismember.return_value = False
        mock_redis_client.sadd.return_value = 1
        mock_redis_client.expire.return_value = True
        mock_redis_client.hset.return_value = 1

        await room_manager.join_room(
            "personality_room", "room123", "user456", "TestUser"
        )

        # Should set TTL on room members, metadata, and user rooms keys
        expire_calls = mock_redis_client.expire.call_args_list
        assert len(expire_calls) >= 3
        # Check that TTL is set to the configured value (3600 in fixture)
        for call in expire_calls:
            assert call[0][1] == 3600
