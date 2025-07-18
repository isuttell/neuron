"""Redis-based session storage for WebSocket sessions."""

import asyncio
import json
import time
from collections.abc import Set as AbstractSet
from typing import Any

import redis.asyncio as redis

from neuron_server.cache import client as redis_client
from neuron_server.controllers.auth import TokenPayload
from neuron_server.logger import logger


class SessionData:
    """Serializable session data for Redis storage."""

    def __init__(  # noqa: PLR0913
        self,
        user_id: str,
        nickname: str,
        session_id: str,
        token_data: dict[str, Any],
        created_at: float | None = None,
        last_active: float | None = None,
    ) -> None:
        self.user_id = user_id
        self.nickname = nickname
        self.session_id = session_id
        self.token_data = token_data
        self.created_at = created_at or time.time()
        self.last_active = last_active or time.time()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Redis storage."""
        return {
            "user_id": self.user_id,
            "nickname": self.nickname,
            "session_id": self.session_id,
            "token_data": json.dumps(self.token_data),
            "created_at": self.created_at,
            "last_active": self.last_active,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionData":
        """Create SessionData from Redis dictionary."""
        return cls(
            user_id=data["user_id"],
            nickname=data["nickname"],
            session_id=data["session_id"],
            token_data=json.loads(data["token_data"]),
            created_at=float(data["created_at"]),
            last_active=float(data["last_active"]),
        )

    def to_token_payload(self) -> TokenPayload:
        """Convert to TokenPayload object."""
        return TokenPayload(**self.token_data)


class RedisSessionStore:
    """Redis-based storage for WebSocket session data."""

    def __init__(self, client: redis.Redis, session_ttl: int = 86400) -> None:
        """Initialize Redis session store.

        Args:
            client: Redis client instance
            session_ttl: Session TTL in seconds (default: 24 hours)
        """
        self._client = client
        self._session_ttl = session_ttl
        self._lock = asyncio.Lock()

    def _session_key(self, session_id: str) -> str:
        """Generate Redis key for session data."""
        return f"session:{session_id}"

    def _user_sessions_key(self, user_id: str) -> str:
        """Generate Redis key for user's session set."""
        return f"user_sessions:{user_id}"

    async def add_session(
        self, session_id: str, user_id: str, nickname: str, token: TokenPayload
    ) -> SessionData:
        """Add a new session to Redis.

        Args:
            session_id: Unique session identifier
            user_id: User ID from token
            nickname: User nickname from token
            token: Token payload data

        Returns:
            SessionData object for the created session
        """
        async with self._lock:
            # Create session data
            session_data = SessionData(
                user_id=user_id,
                nickname=nickname,
                session_id=session_id,
                token_data=token.model_dump(),
            )

            # Store session in Redis with TTL
            session_key = self._session_key(session_id)
            await self._client.hset(session_key, mapping=session_data.to_dict())
            await self._client.expire(session_key, self._session_ttl)

            # Add session to user's session set
            user_sessions_key = self._user_sessions_key(user_id)
            await self._client.sadd(user_sessions_key, session_id)
            await self._client.expire(user_sessions_key, self._session_ttl)

            logger.info(f"Added Redis session {session_id} for user {user_id}")
            return session_data

    async def remove_session(self, session_id: str) -> SessionData | None:
        """Remove a session from Redis.

        Args:
            session_id: Session ID to remove

        Returns:
            SessionData if session existed, None otherwise
        """
        async with self._lock:
            session_key = self._session_key(session_id)

            # Get session data before deletion
            session_dict = await self._client.hgetall(session_key)
            if not session_dict:
                return None

            # Decode bytes to strings
            session_dict = {k.decode(): v.decode() for k, v in session_dict.items()}
            session_data = SessionData.from_dict(session_dict)

            # Remove session
            await self._client.delete(session_key)

            # Remove from user's session set
            user_sessions_key = self._user_sessions_key(session_data.user_id)
            await self._client.srem(user_sessions_key, session_id)

            # Clean up empty user session sets
            user_session_count = await self._client.scard(user_sessions_key)
            if user_session_count == 0:
                await self._client.delete(user_sessions_key)

            logger.info(
                f"Removed Redis session {session_id} for user {session_data.user_id}"
            )
            return session_data

    async def get_session(self, session_id: str) -> SessionData | None:
        """Get session data by ID.

        Args:
            session_id: Session ID to retrieve

        Returns:
            SessionData if found, None otherwise
        """
        session_key = self._session_key(session_id)
        session_dict = await self._client.hgetall(session_key)

        if not session_dict:
            return None

        # Decode bytes to strings
        session_dict = {k.decode(): v.decode() for k, v in session_dict.items()}
        return SessionData.from_dict(session_dict)

    async def get_user_sessions(self, user_id: str) -> list[SessionData]:
        """Get all sessions for a user.

        Args:
            user_id: User ID to get sessions for

        Returns:
            List of SessionData objects for the user
        """
        user_sessions_key = self._user_sessions_key(user_id)
        session_ids = await self._client.smembers(user_sessions_key)

        if not session_ids:
            return []

        # Get all session data in parallel
        session_keys = [self._session_key(sid.decode()) for sid in session_ids]
        session_dicts = await asyncio.gather(
            *[self._client.hgetall(key) for key in session_keys], return_exceptions=True
        )

        sessions = []
        for session_dict in session_dicts:
            if isinstance(session_dict, dict) and session_dict:
                try:
                    # Decode bytes to strings
                    decoded_dict = {
                        k.decode(): v.decode() for k, v in session_dict.items()
                    }
                    sessions.append(SessionData.from_dict(decoded_dict))
                except Exception as e:
                    logger.warning(f"Failed to decode session data: {e}")

        return sessions

    async def get_active_users(self) -> AbstractSet[str]:
        """Get set of all active user IDs.

        Returns:
            Set of user IDs with active sessions
        """
        # Scan for all user_sessions keys
        user_keys = []
        async for key in self._client.scan_iter(match="user_sessions:*"):
            user_keys.append(key.decode())

        # Extract user IDs from keys
        user_ids = set()
        for key in user_keys:
            if key.startswith("user_sessions:"):
                user_id = key[len("user_sessions:") :]
                # Check if the set is not empty
                if await self._client.scard(key) > 0:
                    user_ids.add(user_id)

        return user_ids

    async def update_session_activity(self, session_id: str) -> bool:
        """Update session's last activity timestamp and refresh TTL.

        Args:
            session_id: Session ID to update

        Returns:
            True if session was updated, False if session not found
        """
        session_key = self._session_key(session_id)

        # Check if session exists
        exists = await self._client.exists(session_key)
        if not exists:
            return False

        # Update last_active timestamp
        await self._client.hset(session_key, "last_active", time.time())

        # Refresh TTL
        await self._client.expire(session_key, self._session_ttl)

        # Also refresh user sessions TTL
        session_data = await self.get_session(session_id)
        if session_data:
            user_sessions_key = self._user_sessions_key(session_data.user_id)
            await self._client.expire(user_sessions_key, self._session_ttl)

        return True

    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions and orphaned user session sets.

        Returns:
            Number of sessions cleaned up
        """
        cleaned_count = 0

        # Find all user session keys
        user_session_keys = []
        async for key in self._client.scan_iter(match="user_sessions:*"):
            user_session_keys.append(key.decode())

        for user_sessions_key in user_session_keys:
            # Get all session IDs for this user
            session_ids = await self._client.smembers(user_sessions_key)

            # Check which sessions still exist
            valid_sessions = []
            for session_id in session_ids:
                session_key = self._session_key(session_id.decode())
                if await self._client.exists(session_key):
                    valid_sessions.append(session_id)
                else:
                    cleaned_count += 1

            if valid_sessions:
                # Update the set to only contain valid sessions
                await self._client.delete(user_sessions_key)
                await self._client.sadd(user_sessions_key, *valid_sessions)
                await self._client.expire(user_sessions_key, self._session_ttl)
            else:
                # No valid sessions, delete the user sessions key
                await self._client.delete(user_sessions_key)

        if cleaned_count > 0:
            logger.info(f"Cleaned up {cleaned_count} expired sessions")

        return cleaned_count

    async def get_session_count(self) -> int:
        """Get total number of active sessions."""
        count = 0
        async for _ in self._client.scan_iter(match="session:*"):
            count += 1
        return count

    async def get_user_count(self) -> int:
        """Get total number of active users."""
        active_users = await self.get_active_users()
        return len(active_users)


# Create global Redis session store instance with TTL from config
def create_session_store() -> RedisSessionStore:
    """Create session store with config-based TTL."""
    from neuron_server.config import config

    return RedisSessionStore(redis_client, config.redis.session_ttl)


# Global Redis session store instance
redis_session_store = create_session_store()
