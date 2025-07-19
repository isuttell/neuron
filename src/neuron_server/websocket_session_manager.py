"""WebSocket Session Manager for tracking active connections with user context."""

import asyncio
from collections.abc import Set as AbstractSet
from dataclasses import dataclass

from quart import Websocket

from neuron_server.controllers.auth import TokenPayload
from neuron_server.logger import logger
from neuron_server.redis_session_store import redis_session_store


@dataclass
class WebSocketSession:
    """Represents an active websocket session with user context."""

    websocket: Websocket
    user_id: str
    nickname: str
    session_id: str
    token: TokenPayload


class WebSocketSessionManager:
    """Manages active websocket connections and user sessions with Redis backend."""

    def __init__(self) -> None:
        # Keep only websockets in memory (non-serializable)
        self._websockets: dict[str, Websocket] = {}  # session_id -> websocket
        self._lock = asyncio.Lock()

    async def add_session(
        self, websocket: Websocket, token: TokenPayload, session_id: str
    ) -> WebSocketSession:
        """Add a new websocket session."""
        async with self._lock:
            # Store websocket in memory
            self._websockets[session_id] = websocket

            # Store session data in Redis
            session_data = await redis_session_store.add_session(
                session_id=session_id,
                user_id=token.user_id,
                nickname=token.nickname,
                token=token,
            )

            # Create session object
            session = WebSocketSession(
                websocket=websocket,
                user_id=session_data.user_id,
                nickname=session_data.nickname,
                session_id=session_data.session_id,
                token=session_data.to_token_payload(),
            )

            logger.info(
                f"Added websocket session {session_id} for user {token.user_id}"
            )
            return session

    async def remove_session(self, session_id: str) -> None:
        """Remove a websocket session."""
        async with self._lock:
            # Remove websocket from memory
            self._websockets.pop(session_id, None)

            # Remove session data from Redis
            session_data = await redis_session_store.remove_session(session_id)

            if session_data:
                logger.info(
                    f"Removed websocket session {session_id} "
                    f"for user {session_data.user_id}"
                )

    async def get_session(self, session_id: str) -> WebSocketSession | None:
        """Get a websocket session by ID."""
        # Get session data from Redis
        session_data = await redis_session_store.get_session(session_id)
        if not session_data:
            return None

        # Get websocket from memory
        websocket = self._websockets.get(session_id)
        if not websocket:
            # Websocket not found in memory, session may be stale
            await redis_session_store.remove_session(session_id)
            return None

        # Update session activity
        await redis_session_store.update_session_activity(session_id)

        # Return combined session
        return WebSocketSession(
            websocket=websocket,
            user_id=session_data.user_id,
            nickname=session_data.nickname,
            session_id=session_data.session_id,
            token=session_data.to_token_payload(),
        )

    async def get_user_sessions(self, user_id: str) -> list[WebSocketSession]:
        """Get all active sessions for a user."""
        # Get session data from Redis
        session_data_list = await redis_session_store.get_user_sessions(user_id)

        sessions = []
        for session_data in session_data_list:
            # Check if websocket is still in memory
            websocket = self._websockets.get(session_data.session_id)
            if websocket:
                session = WebSocketSession(
                    websocket=websocket,
                    user_id=session_data.user_id,
                    nickname=session_data.nickname,
                    session_id=session_data.session_id,
                    token=session_data.to_token_payload(),
                )
                sessions.append(session)
            else:
                # Websocket not found, remove stale session
                await redis_session_store.remove_session(session_data.session_id)

        return sessions

    async def get_active_users(self) -> AbstractSet[str]:
        """Get set of all active user IDs."""
        return await redis_session_store.get_active_users()

    async def send_to_user(self, user_id: str, message: str) -> None:
        """Send a message to all sessions for a specific user."""
        sessions = await self.get_user_sessions(user_id)
        if not sessions:
            return

        # Send to all user sessions in parallel
        tasks = []
        for session in sessions:
            tasks.append(self._send_to_session(session, message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _send_to_session(self, session: WebSocketSession, message: str) -> None:
        """Send message to a specific session with error handling."""
        try:
            await session.websocket.send(message)
            # Update session activity on successful send
            await redis_session_store.update_session_activity(session.session_id)
        except Exception as e:
            logger.warning(
                f"Failed to send message to session {session.session_id}: {e}"
            )
            # Session is likely disconnected, remove it
            await self.remove_session(session.session_id)

    async def broadcast_to_users(self, user_ids: list[str], message: str) -> None:
        """Broadcast a message to multiple users."""
        tasks = []
        for user_id in user_ids:
            tasks.append(self.send_to_user(user_id, message))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def get_session_count(self) -> int:
        """Get total number of active sessions."""
        return await redis_session_store.get_session_count()

    async def get_user_count(self) -> int:
        """Get total number of active users."""
        return await redis_session_store.get_user_count()

    async def cleanup_sessions(self) -> int:
        """Clean up expired sessions and return count of cleaned sessions."""
        # Clean up Redis sessions
        redis_cleanup_count = await redis_session_store.cleanup_expired_sessions()

        # Clean up orphaned websockets (those not in Redis)
        orphaned_websockets = []
        for session_id in list(self._websockets.keys()):
            session_data = await redis_session_store.get_session(session_id)
            if not session_data:
                orphaned_websockets.append(session_id)

        # Remove orphaned websockets
        for session_id in orphaned_websockets:
            self._websockets.pop(session_id, None)

        total_cleanup_count = redis_cleanup_count + len(orphaned_websockets)

        if total_cleanup_count > 0:
            logger.info(
                f"Cleaned up {redis_cleanup_count} Redis sessions and "
                f"{len(orphaned_websockets)} orphaned websockets"
            )

        return total_cleanup_count


# Global session manager instance
session_manager = WebSocketSessionManager()
