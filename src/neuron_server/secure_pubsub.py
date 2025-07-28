"""Secure pub/sub service with permission-based message routing."""

from uuid import UUID

from pydantic import BaseModel

from neuron_server.controllers.events.media_events import MediaEvent
from neuron_server.controllers.events.message_events import (
    MessageEvent,
    PartialMessageEvent,
)
from neuron_server.controllers.events.thread_events import (
    CancelRequestEvent,
    GetThreadResponse,
)
from neuron_server.logger import logger
from neuron_server.permission_service import permission_service
from neuron_server.pubsub import pubsub as base_pubsub
from neuron_server.room_manager import room_manager
from neuron_server.websocket_session_manager import session_manager


class SecurePubSub:
    """Secure pub/sub service that routes messages based on user permissions."""

    def __init__(self) -> None:
        self.base_pubsub = base_pubsub

    async def publish_to_user(self, user_id: str, event: BaseModel) -> None:
        """Publish an event directly to a specific user."""
        user_channel = f"user:{user_id}"
        await self.base_pubsub.publish(user_channel, event)

    async def publish_to_users(self, user_ids: list[str], event: BaseModel) -> None:
        """Publish an event to multiple specific users."""
        for user_id in user_ids:
            await self.publish_to_user(user_id, event)

    async def publish_thread_message(self, message_event: MessageEvent) -> None:
        """Publish a thread message to users with access to the thread."""
        thread_message = message_event.message
        if not hasattr(thread_message, "thread_id") or not thread_message.thread_id:
            logger.warning(
                "Thread message missing thread_id, skipping permission check"
            )
            return

        # Get users with access to this thread
        authorized_users = await permission_service.get_users_with_thread_access(
            thread_message.thread_id
        )

        if not authorized_users:
            logger.debug(f"No users have access to thread {thread_message.thread_id}")
            return

        # Send to authorized users only
        await self.publish_to_users(authorized_users, message_event)

    async def publish_partial_message(self, partial_event: PartialMessageEvent) -> None:
        """Publish a partial message to users with access to the thread."""
        partial_message = partial_event.message
        if not hasattr(partial_message, "thread_id") or not partial_message.thread_id:
            logger.warning(
                "Partial message missing thread_id, skipping permission check"
            )
            return

        # Get users with access to this thread
        authorized_users = await permission_service.get_users_with_thread_access(
            partial_message.thread_id
        )

        if not authorized_users:
            logger.debug(f"No users have access to thread {partial_message.thread_id}")
            return

        # Send to authorized users only
        await self.publish_to_users(authorized_users, partial_event)

    async def publish_thread_update(self, thread_event: GetThreadResponse) -> None:
        """Publish a thread update to users with access to the thread."""
        thread = thread_event.thread
        if not thread.id:
            logger.warning("Thread update missing thread ID, skipping permission check")
            return

        # Get users with access to this thread
        authorized_users = await permission_service.get_users_with_thread_access(
            thread.id
        )

        if not authorized_users:
            logger.debug(f"No users have access to thread {thread.id}")
            return

        # Send to authorized users only
        await self.publish_to_users(authorized_users, thread_event)

    async def publish_thread_cancellation(
        self, cancel_event: CancelRequestEvent
    ) -> None:
        """Publish a thread cancellation to users with access to the thread."""
        thread_id = cancel_event.thread_id
        if not thread_id:
            logger.warning(
                "Cancellation event missing thread_id, skipping permission check"
            )
            return

        # Get users with access to this thread
        authorized_users = await permission_service.get_users_with_thread_access(
            thread_id
        )

        if not authorized_users:
            logger.debug(f"No users have access to thread {thread_id}")
            return

        # Send to authorized users only
        await self.publish_to_users(authorized_users, cancel_event)

    async def publish_media_event(self, media_event: MediaEvent) -> None:
        """Publish a media event to users with access to the associated thread."""
        # Check if any media items have thread_id for permission checking
        thread_ids = set()
        for media_item in media_event.media:
            if hasattr(media_item, "thread_id") and media_item.thread_id:
                thread_ids.add(media_item.thread_id)

        if not thread_ids:
            logger.error("Media event has no associated thread_ids")
            return

        # Get all users with access to any of the associated threads
        all_authorized_users = set()
        for thread_id in thread_ids:
            thread_users = await permission_service.get_users_with_thread_access(
                thread_id
            )
            all_authorized_users.update(thread_users)

        if not all_authorized_users:
            logger.debug(f"No users have access to threads {thread_ids}")
            return

        # Send to authorized users only
        await self.publish_to_users(list(all_authorized_users), media_event)

    async def publish_personality_event(
        self, personality_id: UUID, event: BaseModel
    ) -> None:
        """Publish an event to users with access to a personality."""
        # Get users with access to this personality
        authorized_users = await permission_service.get_users_with_personality_access(
            personality_id
        )

        if not authorized_users:
            logger.debug(f"No users have access to personality {personality_id}")
            return

        # Send to authorized users only
        await self.publish_to_users(authorized_users, event)

    async def publish_personality_room_message(
        self, personality_id: UUID, room_id: UUID, event: BaseModel
    ) -> None:
        """Publish a personality message to users in a specific personality room."""
        # Get users currently in the specific personality room
        room_members = await room_manager.get_room_members(
            "personality_room", str(room_id)
        )

        if not room_members:
            logger.debug(f"No users in personality room {room_id}")
            return

        # Also check permissions to ensure room members have access
        authorized_users = await permission_service.get_users_with_personality_access(
            personality_id
        )

        # Only send to users who are both in the room AND have permission
        room_authorized_users = [
            user_id for user_id in room_members if user_id in authorized_users
        ]

        if not room_authorized_users:
            logger.debug(
                f"No authorized users in personality room {room_id}"
            )
            return

        # Update room activity
        await room_manager.update_room_activity("personality_room", str(room_id))

        # Send to authorized room members only
        await self.publish_to_users(room_authorized_users, event)
        logger.debug(
            f"Published personality room message to {len(room_authorized_users)} "
            f"users in room {room_id}"
        )

    async def publish_error_to_user(self, user_id: str, error_event: BaseModel) -> None:
        """Publish an error event to a specific user."""
        await self.publish_to_user(user_id, error_event)

    async def broadcast_to_all_users(self, event: BaseModel) -> None:
        """Broadcast an event to all currently connected users.

        Use sparingly - most events should be permission-based.
        """
        active_users = await session_manager.get_active_users()
        if active_users:
            await self.publish_to_users(list(active_users), event)

    async def publish_admin_event(self, event: BaseModel) -> None:
        """Publish an event to admin users only.

        Note: This is a placeholder - implement admin role checking as needed.
        """
        # TODO: Implement admin role checking when user roles are available
        logger.warning("Admin event publishing not implemented yet")

    async def publish_system_event(self, event: BaseModel) -> None:
        """Publish a system-wide event (e.g., maintenance notifications).

        These bypass permission checks but should be used sparingly.
        """
        await self.broadcast_to_all_users(event)


# Global secure pubsub instance
secure_pubsub = SecurePubSub()
