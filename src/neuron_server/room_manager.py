"""Room manager for real-time personality chat rooms using Redis."""

import asyncio
import time
from typing import Any
from uuid import UUID

import redis.asyncio as redis

from neuron_server.cache import client as redis_client
from neuron_server.logger import logger


class RoomManager:
    """Manages room membership for real-time messaging using Redis."""

    def __init__(self, client: redis.Redis, room_ttl: int = 86400) -> None:
        """Initialize room manager.

        Args:
            client: Redis client instance
            room_ttl: Room TTL in seconds (default: 24 hours)
        """
        self._client = client
        self._room_ttl = room_ttl
        self._lock = asyncio.Lock()

    def _room_members_key(self, room_type: str, room_id: str) -> str:
        """Generate Redis key for room members set."""
        return f"room:{room_type}:{room_id}:members"

    def _room_metadata_key(self, room_type: str, room_id: str) -> str:
        """Generate Redis key for room metadata."""
        return f"room:{room_type}:{room_id}:metadata"

    def _user_rooms_key(self, user_id: str) -> str:
        """Generate Redis key for user's rooms set."""
        return f"user:{user_id}:rooms"

    async def join_room(
        self, room_type: str, room_id: str, user_id: str, nickname: str
    ) -> bool:
        """Add a user to a room.

        Args:
            room_type: Type of room (e.g., 'personality_room', 'thread')
            room_id: Room identifier
            user_id: User ID joining the room
            nickname: User nickname for display

        Returns:
            True if user was added to room, False if already in room
        """
        async with self._lock:
            room_members_key = self._room_members_key(room_type, room_id)
            room_metadata_key = self._room_metadata_key(room_type, room_id)
            user_rooms_key = self._user_rooms_key(user_id)

            # Check if user is already in room
            is_member = await self._client.sismember(room_members_key, user_id)
            if is_member:
                # Refresh TTL even if already member
                await self._client.expire(room_members_key, self._room_ttl)
                await self._client.expire(room_metadata_key, self._room_ttl)
                await self._client.expire(user_rooms_key, self._room_ttl)
                return False

            # Add user to room members
            await self._client.sadd(room_members_key, user_id)
            await self._client.expire(room_members_key, self._room_ttl)

            # Update room metadata
            room_identifier = f"{room_type}:{room_id}"
            metadata = {
                "room_type": room_type,
                "room_id": room_id,
                "created_at": time.time(),
                "last_activity": time.time(),
            }
            await self._client.hset(room_metadata_key, mapping=metadata)
            await self._client.expire(room_metadata_key, self._room_ttl)

            # Add room to user's rooms set
            await self._client.sadd(user_rooms_key, room_identifier)
            await self._client.expire(user_rooms_key, self._room_ttl)

            return True

    async def leave_room(self, room_type: str, room_id: str, user_id: str) -> bool:
        """Remove a user from a room.

        Args:
            room_type: Type of room
            room_id: Room identifier
            user_id: User ID leaving the room

        Returns:
            True if user was removed from room, False if not in room
        """
        async with self._lock:
            room_members_key = self._room_members_key(room_type, room_id)
            user_rooms_key = self._user_rooms_key(user_id)
            room_identifier = f"{room_type}:{room_id}"

            # Check if user is in room
            is_member = await self._client.sismember(room_members_key, user_id)
            if not is_member:
                return False

            # Remove user from room
            await self._client.srem(room_members_key, user_id)

            # Remove room from user's rooms
            await self._client.srem(user_rooms_key, room_identifier)

            # Clean up empty sets
            member_count = await self._client.scard(room_members_key)
            if member_count == 0:
                room_metadata_key = self._room_metadata_key(room_type, room_id)
                await self._client.delete(room_members_key)
                await self._client.delete(room_metadata_key)

            user_room_count = await self._client.scard(user_rooms_key)
            if user_room_count == 0:
                await self._client.delete(user_rooms_key)

            return True

    async def get_room_members(self, room_type: str, room_id: str) -> list[str]:
        """Get all members of a room.

        Args:
            room_type: Type of room
            room_id: Room identifier

        Returns:
            List of user IDs in the room
        """
        room_members_key = self._room_members_key(room_type, room_id)
        members = await self._client.smembers(room_members_key)
        return [member.decode() for member in members]

    async def get_user_rooms(self, user_id: str) -> list[dict[str, Any]]:
        """Get all rooms a user is in.

        Args:
            user_id: User ID

        Returns:
            List of room info dictionaries with room_type and room_id
        """
        user_rooms_key = self._user_rooms_key(user_id)
        room_identifiers = await self._client.smembers(user_rooms_key)

        rooms = []
        for room_identifier in room_identifiers:
            room_str = room_identifier.decode()
            if ":" in room_str:
                room_type, room_id = room_str.split(":", 1)
                rooms.append({"room_type": room_type, "room_id": room_id})

        return rooms

    async def is_user_in_room(self, room_type: str, room_id: str, user_id: str) -> bool:
        """Check if a user is in a specific room.

        Args:
            room_type: Type of room
            room_id: Room identifier
            user_id: User ID to check

        Returns:
            True if user is in room, False otherwise
        """
        room_members_key = self._room_members_key(room_type, room_id)
        return await self._client.sismember(room_members_key, user_id)

    async def update_room_activity(self, room_type: str, room_id: str) -> bool:
        """Update room's last activity timestamp and refresh TTL.

        Args:
            room_type: Type of room
            room_id: Room identifier

        Returns:
            True if room was updated, False if room not found
        """
        room_metadata_key = self._room_metadata_key(room_type, room_id)

        # Check if room exists
        exists = await self._client.exists(room_metadata_key)
        if not exists:
            return False

        # Update last_activity timestamp
        await self._client.hset(room_metadata_key, "last_activity", time.time())

        # Refresh TTL for room metadata and members
        room_members_key = self._room_members_key(room_type, room_id)
        await self._client.expire(room_metadata_key, self._room_ttl)
        await self._client.expire(room_members_key, self._room_ttl)

        return True

    async def cleanup_user_from_all_rooms(self, user_id: str) -> int:
        """Remove user from all rooms (called on disconnect).

        Args:
            user_id: User ID to remove from all rooms

        Returns:
            Number of rooms user was removed from
        """
        user_rooms = await self.get_user_rooms(user_id)
        cleanup_count = 0

        for room_info in user_rooms:
            room_type = room_info["room_type"]
            room_id = room_info["room_id"]
            if await self.leave_room(room_type, room_id, user_id):
                cleanup_count += 1

        if cleanup_count > 0:
            logger.info(f"Cleaned up user {user_id} from {cleanup_count} rooms")

        return cleanup_count

    async def join_personality_room(
        self, personality_id: UUID, user_id: str, nickname: str
    ) -> bool:
        """Convenience method to join a personality chat room.

        Args:
            personality_id: Personality UUID
            user_id: User ID joining
            nickname: User nickname

        Returns:
            True if user joined room, False if already in room
        """
        return await self.join_room(
            "personality_room", str(personality_id), user_id, nickname
        )

    async def leave_personality_room(self, personality_id: UUID, user_id: str) -> bool:
        """Convenience method to leave a personality chat room.

        Args:
            personality_id: Personality UUID
            user_id: User ID leaving

        Returns:
            True if user left room, False if not in room
        """
        return await self.leave_room("personality_room", str(personality_id), user_id)

    async def get_personality_room_members(self, personality_id: UUID) -> list[str]:
        """Get all members of a personality chat room.

        Args:
            personality_id: Personality UUID

        Returns:
            List of user IDs in the personality room
        """
        return await self.get_room_members("personality_room", str(personality_id))


# Create global room manager instance
def create_room_manager() -> RoomManager:
    """Create room manager with config-based TTL."""
    from neuron_server.config import config

    return RoomManager(redis_client, config.redis.session_ttl)


# Global room manager instance
room_manager = create_room_manager()
