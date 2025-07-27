import asyncio
from uuid import UUID

from pydantic import BaseModel, Field
from quart import Blueprint, Response
from werkzeug.exceptions import Forbidden, NotFound

from neuron_server.controllers.auth import requires_auth
from neuron_server.controllers.csrf import requires_csrf
from neuron_server.controllers.events.message_events import (
    PersonalityMessageDeletedEvent,
    PersonalityMessageEvent,
)
from neuron_server.controllers.events.room_events import (
    JoinPersonalityRoom,
    LeavePersonalityRoom,
    RoomJoinedEvent,
    RoomLeftEvent,
    UserJoinedRoomEvent,
    UserLeftRoomEvent,
)
from neuron_server.event_router import EventRouter
from neuron_server.logger import logger
from neuron_server.models.personality_message_media_item_model import (
    PersonalityMessageMediaItemModel,
)
from neuron_server.models.personality_message_model import PersonalityMessageModel
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.models.personality_room_model import PersonalityRoomModel
from neuron_server.permission_service import permission_service
from neuron_server.room_manager import room_manager
from neuron_server.secure_pubsub import secure_pubsub
from neuron_server.services.personality_chat_orchestrator import (
    PersonalityChatOrchestrator,
)
from neuron_server.type_defs.request_proxy import request
from neuron_server.websocket_session_manager import WebSocketSession

blueprint = Blueprint("personality_message", __name__)
router = EventRouter()

# Initialize the chat orchestrator
chat_orchestrator = PersonalityChatOrchestrator()


class CreatePersonalityMessage(BaseModel):
    content: str = Field(description="The message content")
    room_id: UUID = Field(description="The ID of the room to create the message in")


class UpdatePersonalityMessage(BaseModel):
    content: str = Field(description="The updated message content")


@blueprint.get("/<uuid:personality_id>")
@requires_auth
async def get_personality_messages(personality_id: UUID) -> dict[str, list[dict]]:
    """Get messages for a personality.

    Args:
        personality_id: The ID of the personality to get messages for

    Returns:
        A dictionary with a list of personality messages

    Raises:
        NotFound: If the personality doesn't exist or user doesn't have access
    """
    user_id = request.token.user_id

    # Check if user has access to the personality
    personality = await PersonalityModel.get_for_user(
        personality_id=personality_id, user_id=user_id
    )
    if not personality:
        raise NotFound(
            f"Personality with id {personality_id} not found or you don't have access"
        )

    # Get query parameters for pagination and filtering
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))
    room_id_str = request.args.get("room_id", None)
    room_id = UUID(room_id_str) if room_id_str else None

    # Validate pagination parameters
    limit = min(limit, 100)
    if limit < 1:
        limit = 50
    offset = max(offset, 0)

    # If room_id is provided, verify user has access to the room
    if room_id:
        room = await PersonalityRoomModel.get_for_user(room_id, user_id, personality_id)
        if not room:
            raise NotFound(f"Room with id {room_id} not found or you don't have access")

    # Get messages for the personality
    messages = await PersonalityMessageModel.list(
        personality_id=personality_id, room_id=room_id, limit=limit, offset=offset
    )

    # Get all users who have access to this personality
    users_dict = await chat_orchestrator.get_personality_users_dict(personality_id)
    users = list(users_dict.values())

    # Get media items for each message and include them in the response
    messages_with_media = []
    for message in messages:
        message_data = message.model_dump()
        # Get associated media items
        media_items = await PersonalityMessageMediaItemModel.get_media_for_message(
            message.id
        )
        message_data["media_items"] = [item.model_dump() for item in media_items]
        messages_with_media.append(message_data)

    return {
        "personality_messages": messages_with_media,
        "personality": personality.model_dump(),
        "users": [user.model_dump() for user in users],
    }


@blueprint.post("/<uuid:personality_id>")
@requires_auth
@requires_csrf
async def create_personality_message(personality_id: UUID) -> dict[str, dict]:
    """Create a new message for a personality.

    Args:
        personality_id: The ID of the personality to create a message for

    Returns:
        A dictionary with the created message

    Raises:
        NotFound: If the personality doesn't exist or user doesn't have access
        BadRequest: If the request data is invalid
    """
    user_id = request.token.user_id

    # Check if user has access to the personality
    personality = await PersonalityModel.get_for_user(
        personality_id=personality_id, user_id=user_id
    )
    if not personality:
        raise NotFound(
            f"Personality with id {personality_id} not found or you don't have access"
        )

    # Note: Allow messages even when personality is busy
    # Quick responses will be handled during analysis

    # Parse request body
    body = await request.get_json()
    payload = CreatePersonalityMessage(**body)

    # Verify user has access to the room
    room = await PersonalityRoomModel.get_for_user(
        payload.room_id, user_id, personality_id
    )
    if not room:
        raise NotFound(
            f"Room with id {payload.room_id} not found or you don't have access"
        )

    # Create the message
    create_params = PersonalityMessageModel.CreateParams(
        personality_id=personality_id,
        personality_room_id=payload.room_id,
        content=payload.content,
        user_id=user_id,  # Message is from the user
    )
    message = await PersonalityMessageModel.create(params=create_params)

    # Update room message count
    await PersonalityRoomModel.update_message_count(payload.room_id, increment=1)

    # Broadcast the new message to users in the personality chat room
    message_event = PersonalityMessageEvent(
        personality_id=personality_id,
        message_id=message.id,
        content=message.content,
        user_id=message.user_id,
        created_at=message.created_at.isoformat(),
        updated_at=message.updated_at.isoformat(),
    )
    await secure_pubsub.publish_personality_room_message(personality_id, message_event)

    # Start background task to analyze message direction (non-blocking)
    asyncio.create_task(
        chat_orchestrator.process_user_message(personality_id, message.id)
    )

    return {"personality_message": message.model_dump()}


@blueprint.put("/<uuid:personality_id>/messages/<uuid:message_id>")
@requires_auth
@requires_csrf
async def update_personality_message(
    personality_id: UUID, message_id: UUID
) -> dict[str, dict]:
    """Update a personality message.

    Args:
        personality_id: The ID of the personality
        message_id: The ID of the message to update

    Returns:
        A dictionary with the updated message

    Raises:
        NotFound: If the personality or message doesn't exist or user lacks access
        Forbidden: If the user doesn't own the message
    """
    user_id = request.token.user_id

    # Check if user has access to the personality
    personality = await PersonalityModel.get_for_user(
        personality_id=personality_id, user_id=user_id
    )
    if not personality:
        raise NotFound(
            f"Personality with id {personality_id} not found or you don't have access"
        )

    # Get the message to verify ownership
    message = await PersonalityMessageModel.get(message_id)
    if not message:
        raise NotFound(f"Message with id {message_id} not found")

    # Verify the message belongs to this personality
    if message.personality_id != personality_id:
        raise NotFound(f"Message does not belong to personality {personality_id}")

    # Verify the user owns the message (can't edit personality responses)
    if message.user_id != user_id:
        raise Forbidden("You can only edit your own messages")

    # Parse request body
    body = await request.get_json()
    payload = UpdatePersonalityMessage(**body)

    # Update the message
    update_params = PersonalityMessageModel.UpdateParams(
        message_id=message_id,
        content=payload.content,
    )
    updated_message = await PersonalityMessageModel.update(params=update_params)

    if not updated_message:
        raise NotFound(f"Message with id {message_id} not found")

    # Broadcast the updated message to users in the personality chat room
    message_event = PersonalityMessageEvent(
        personality_id=personality_id,
        message_id=updated_message.id,
        content=updated_message.content,
        user_id=updated_message.user_id,
        created_at=updated_message.created_at.isoformat(),
        updated_at=updated_message.updated_at.isoformat(),
    )
    await secure_pubsub.publish_personality_room_message(personality_id, message_event)

    return {"personality_message": updated_message.model_dump()}


@blueprint.delete("/<uuid:personality_id>/messages/<uuid:message_id>")
@requires_auth
@requires_csrf
async def delete_personality_message(
    personality_id: UUID, message_id: UUID
) -> Response:
    """Delete a personality message.

    Args:
        personality_id: The ID of the personality
        message_id: The ID of the message to delete

    Returns:
        204 No Content

    Raises:
        NotFound: If the personality or message doesn't exist or user lacks access
        Forbidden: If the user doesn't have permission to delete the message
    """
    user_id = request.token.user_id

    # Check if user has admin access to the personality
    has_admin = await PersonalityModel.has_admin_access(
        personality_id=personality_id, user_id=user_id
    )

    # If not admin, check if user has regular access and owns the message
    if not has_admin:
        personality = await PersonalityModel.get_for_user(
            personality_id=personality_id, user_id=user_id
        )
        if not personality:
            raise NotFound(
                f"Personality {personality_id} not found or you don't have access"
            )

        # Get the message to verify ownership
        message = await PersonalityMessageModel.get(message_id)
        if not message:
            raise NotFound(f"Message with id {message_id} not found")

        # Verify the message belongs to this personality
        if message.personality_id != personality_id:
            raise NotFound(f"Message does not belong to personality {personality_id}")

        # Non-admin users can only delete their own messages
        if message.user_id != user_id:
            raise Forbidden("You can only delete your own messages")
    else:
        # Admin can delete any message, but verify message exists
        message = await PersonalityMessageModel.get(message_id)
        if not message:
            raise NotFound(f"Message with id {message_id} not found")

        if message.personality_id != personality_id:
            raise NotFound(f"Message does not belong to personality {personality_id}")

    # Delete the message
    await PersonalityMessageModel.delete(message_id)

    # Update room message count
    if message.personality_room_id:
        await PersonalityRoomModel.update_message_count(
            message.personality_room_id, increment=-1
        )

    # Broadcast the message deletion to users in the personality chat room
    delete_event = PersonalityMessageDeletedEvent(
        personality_id=personality_id,
        message_id=message_id,
    )
    await secure_pubsub.publish_personality_room_message(personality_id, delete_event)

    return Response(status=204)


@router.on(JoinPersonalityRoom)
async def ajoin_personality_room(
    event: JoinPersonalityRoom, session: WebSocketSession | None = None
) -> None:
    """Handle joining a personality chat room with permission checks."""
    if not session:
        logger.error("JoinPersonalityRoom event received without session context")
        return

    user_id = session.user_id
    nickname = session.nickname
    personality_id = event.personality_id

    # Check if user has access to this personality
    has_access = await permission_service.user_has_personality_access(
        user_id, personality_id
    )
    if not has_access:
        logger.warning(
            f"User {user_id} denied access to personality room {personality_id}"
        )
        return

    # Join the personality room
    # Debug: Check room state before join
    current_members = await room_manager.get_personality_room_members(personality_id)
    logger.debug(
        f"Current members in room {personality_id} before join: {current_members}"
    )

    joined = await room_manager.join_personality_room(personality_id, user_id, nickname)

    if joined:
        # Send confirmation to the user who joined
        member_count = len(
            await room_manager.get_personality_room_members(personality_id)
        )
        join_event = RoomJoinedEvent(
            room_type="personality",
            room_id=str(personality_id),
            member_count=member_count,
        )
        await secure_pubsub.publish_to_user(user_id, join_event)

        # Notify other room members that this user joined
        room_members = await room_manager.get_personality_room_members(personality_id)
        other_members = [member for member in room_members if member != user_id]

        if other_members:
            user_joined_event = UserJoinedRoomEvent(
                room_type="personality",
                room_id=str(personality_id),
                user_id=user_id,
                nickname=nickname,
            )
            await secure_pubsub.publish_to_users(other_members, user_joined_event)

        logger.info(
            f"User {user_id} ({nickname}) joined personality room {personality_id}"
        )
    else:
        # User already in room - treat as successful rejoin
        # Send confirmation to the user so their client state updates
        member_count = len(
            await room_manager.get_personality_room_members(personality_id)
        )
        join_event = RoomJoinedEvent(
            room_type="personality",
            room_id=str(personality_id),
            member_count=member_count,
        )
        await secure_pubsub.publish_to_user(user_id, join_event)

        logger.info(
            f"User {user_id} ({nickname}) rejoined personality room {personality_id}"
        )


@router.on(LeavePersonalityRoom)
async def aleave_personality_room(
    event: LeavePersonalityRoom, session: WebSocketSession | None = None
) -> None:
    """Handle leaving a personality chat room."""
    if not session:
        logger.error("LeavePersonalityRoom event received without session context")
        return

    user_id = session.user_id
    nickname = session.nickname
    personality_id = event.personality_id

    # Get current room members before leaving
    room_members = await room_manager.get_personality_room_members(personality_id)
    other_members = [member for member in room_members if member != user_id]

    # Leave the personality room
    left = await room_manager.leave_personality_room(personality_id, user_id)

    if left:
        # Send confirmation to the user who left
        leave_event = RoomLeftEvent(
            room_type="personality", room_id=str(personality_id)
        )
        await secure_pubsub.publish_to_user(user_id, leave_event)

        # Notify other room members that this user left
        if other_members:
            user_left_event = UserLeftRoomEvent(
                room_type="personality",
                room_id=str(personality_id),
                user_id=user_id,
                nickname=nickname,
            )
            await secure_pubsub.publish_to_users(other_members, user_left_event)

        logger.info(
            f"User {user_id} ({nickname}) left personality room {personality_id}"
        )
    else:
        logger.debug(f"User {user_id} was not in personality room {personality_id}")


async def cleanup_user_personality_rooms(session: WebSocketSession) -> None:
    """Clean up user from all personality rooms when they disconnect."""
    user_id = session.user_id
    nickname = session.nickname
    logger.info(f"Starting cleanup of user {user_id} from all personality rooms")

    # Get all rooms the user is in
    user_rooms = await room_manager.get_user_rooms(user_id)
    logger.info(f"Found {len(user_rooms)} rooms for user {user_id}: {user_rooms}")

    for room_info in user_rooms:
        room_type = room_info["room_type"]
        room_id = room_info["room_id"]

        # Only clean up personality rooms since this controller only handles those
        if room_type != "personality":
            continue

        # Get current room members before leaving
        room_members = await room_manager.get_room_members(room_type, room_id)
        other_members = [member for member in room_members if member != user_id]

        # Leave the room
        left = await room_manager.leave_room(room_type, room_id, user_id)
        logger.info(f"User {user_id} left room {room_type}:{room_id} - success: {left}")

        if left and other_members:
            # Notify other room members that this user left
            user_left_event = UserLeftRoomEvent(
                room_type=room_type, room_id=room_id, user_id=user_id, nickname=nickname
            )
            await secure_pubsub.publish_to_users(other_members, user_left_event)

    # Also use the room manager's cleanup method for personality rooms
    await room_manager.cleanup_user_from_all_rooms(user_id)
