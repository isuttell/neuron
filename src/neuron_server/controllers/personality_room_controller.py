from uuid import UUID

from pydantic import BaseModel, Field
from quart import Blueprint, Response
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from neuron_server.controllers.auth import requires_auth
from neuron_server.controllers.csrf import requires_csrf
from neuron_server.controllers.events.personality_room_events import (
    PersonalityRoomCreatedEvent,
    PersonalityRoomDeletedEvent,
    PersonalityRoomUpdatedEvent,
    UserJoinedPersonalityRoomEvent,
    UserLeftPersonalityRoomEvent,
)
from neuron_server.decorators import rate_limit
from neuron_server.event_router import EventRouter
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.models.personality_room_model import PersonalityRoomModel
from neuron_server.models.personality_room_user_model import PersonalityRoomUserModel
from neuron_server.models.user_model import UserModel
from neuron_server.secure_pubsub import secure_pubsub
from neuron_server.type_defs.request_proxy import request

blueprint = Blueprint("personality_room", __name__)
router = EventRouter()


class CreatePersonalityRoom(BaseModel):
    name: str = Field(description="The name of the room")
    type: str = Field(description="Room type: private or shared", default="private")


class UpdatePersonalityRoom(BaseModel):
    name: str | None = Field(description="The updated room name", default=None)
    type: str | None = Field(description="The updated room type", default=None)


class PersonalityRoomUserPayload(BaseModel):
    user_id: str
    role: str = "user"


async def check_personality_access(personality_id: UUID, user_id: str) -> None:
    """Check if user has access to a personality.

    Args:
        personality_id: The ID of the personality
        user_id: The ID of the user

    Raises:
        NotFound: If personality doesn't exist or user doesn't have access
    """
    personality = await PersonalityModel.get_for_user(
        personality_id=personality_id, user_id=user_id
    )
    if not personality:
        raise NotFound(
            f"Personality with id {personality_id} not found or you don't have access"
        )


@blueprint.get("/<uuid:personality_id>")
@requires_auth
async def get_personality_rooms(personality_id: UUID) -> dict[str, list[dict]]:
    """Get all rooms for a personality that the user has access to.

    Args:
        personality_id: The ID of the personality

    Returns:
        A dictionary with a list of rooms

    Raises:
        NotFound: If personality doesn't exist or user doesn't have access
    """
    user_id = request.token.user_id

    # Check personality access
    await check_personality_access(personality_id, user_id)

    # Get accessible rooms
    rooms = await PersonalityRoomModel.list_for_personality(personality_id, user_id)

    # Get room users for all rooms
    room_ids = [room.id for room in rooms]
    all_room_users = await PersonalityRoomUserModel.get_bulk_room_users(room_ids)

    # Get unique user IDs from room users
    user_ids = list({ru.user_id for ru in all_room_users})

    # Add creators to user list
    creator_ids = [room.created_by for room in rooms if room.created_by]
    user_ids.extend(creator_ids)
    user_ids = list(set(user_ids))

    # Get user details
    users = await UserModel.get_by_ids(user_ids) if user_ids else []

    # Build response with room details and associated users
    rooms_data = []
    for room in rooms:
        room_data = room.model_dump()

        # Get users for this room
        room_user_ids = [
            ru.user_id for ru in all_room_users if ru.personality_room_id == room.id
        ]
        # Add creator if not already in list
        if room.created_by and room.created_by not in room_user_ids:
            room_user_ids.append(room.created_by)

        # Add user count
        room_data["user_count"] = len(room_user_ids)

        rooms_data.append(room_data)

    return {
        "personality_rooms": rooms_data,
        "users": [user.model_dump() for user in users],
    }


@blueprint.post("/<uuid:personality_id>")
@requires_auth
@requires_csrf
@rate_limit(limit_type="create")
async def create_personality_room(personality_id: UUID) -> dict[str, dict]:
    """Create a new room for a personality.

    Args:
        personality_id: The ID of the personality

    Returns:
        A dictionary with the created room

    Raises:
        NotFound: If personality doesn't exist or user doesn't have access
        BadRequest: If the request data is invalid
    """
    user_id = request.token.user_id

    # Check personality access
    await check_personality_access(personality_id, user_id)

    # Parse request body
    body = await request.get_json()
    payload = CreatePersonalityRoom(**body)

    # Validate room type
    if payload.type not in ["private", "shared"]:
        raise BadRequest("Room type must be 'private' or 'shared'")

    # Create the room
    create_params = PersonalityRoomModel.CreateParams(
        personality_id=personality_id,
        name=payload.name,
        type=payload.type,
        created_by=user_id,
    )
    room = await PersonalityRoomModel.create(params=create_params)

    # If private room, automatically add creator as admin
    if room.type == "private":
        room_user_params = PersonalityRoomUserModel.CreateParams(
            personality_room_id=room.id,
            user_id=user_id,
            role="admin",
        )
        await PersonalityRoomUserModel.create(params=room_user_params)

    # Broadcast room creation event
    room_event = PersonalityRoomCreatedEvent(
        personality_id=personality_id,
        room_id=room.id,
        name=room.name,
        room_type=room.type,
        created_by=room.created_by,
        message_count=room.message_count,
    )
    await secure_pubsub.publish_personality_room_message(personality_id, room_event)

    return {"personality_room": room.model_dump()}


@blueprint.get("/<uuid:personality_id>/rooms/<uuid:room_id>")
@requires_auth
async def get_personality_room(
    personality_id: UUID, room_id: UUID
) -> dict[str, dict | list[dict]]:
    """Get details for a specific personality room.

    Args:
        personality_id: The ID of the personality
        room_id: The ID of the room

    Returns:
        A dictionary with the room details and users

    Raises:
        NotFound: If room doesn't exist or user doesn't have access
    """
    user_id = request.token.user_id

    # Check personality access first
    await check_personality_access(personality_id, user_id)

    # Get room with permission check
    room = await PersonalityRoomModel.get_for_user(room_id, user_id, personality_id)
    if not room:
        raise NotFound(f"Room with id {room_id} not found or you don't have access")

    # Get room users
    room_users = await PersonalityRoomUserModel.get_room_users(room_id)
    user_ids = [ru.user_id for ru in room_users]

    # Add creator if not in list
    if room.created_by and room.created_by not in user_ids:
        user_ids.append(room.created_by)

    # Get user details
    users = await UserModel.get_by_ids(user_ids) if user_ids else []

    # Add roles to users
    users_data = []
    for user in users:
        user_data = user.model_dump()
        # Find role from room_users or check if creator
        if user.id == room.created_by:
            user_data["role"] = "admin"
        else:
            for ru in room_users:
                if ru.user_id == user.id:
                    user_data["role"] = ru.role
                    break
        users_data.append(user_data)

    return {
        "personality_room": room.model_dump(),
        "users": users_data,
    }


@blueprint.put("/<uuid:personality_id>/rooms/<uuid:room_id>")
@requires_auth
@requires_csrf
async def update_personality_room(
    personality_id: UUID, room_id: UUID
) -> dict[str, dict]:
    """Update a personality room.

    Args:
        personality_id: The ID of the personality
        room_id: The ID of the room to update

    Returns:
        A dictionary with the updated room

    Raises:
        NotFound: If room doesn't exist
        Forbidden: If user doesn't have admin access
        BadRequest: If the request data is invalid
    """
    user_id = request.token.user_id

    # Check personality access
    await check_personality_access(personality_id, user_id)

    # Check if user has admin access to the room
    has_admin = await PersonalityRoomModel.has_admin_access(room_id, user_id)
    if not has_admin:
        raise Forbidden("You do not have permission to update this room")

    # Parse request body
    body = await request.get_json()
    payload = UpdatePersonalityRoom(**body)

    # Validate room type if provided
    if payload.type and payload.type not in ["private", "shared"]:
        raise BadRequest("Room type must be 'private' or 'shared'")

    # Update the room
    update_params = PersonalityRoomModel.UpdateParams(
        room_id=room_id,
        name=payload.name,
        type=payload.type,
    )
    room = await PersonalityRoomModel.update(params=update_params)

    if not room:
        raise NotFound(f"Room with id {room_id} not found")

    # Broadcast room update event
    update_event = PersonalityRoomUpdatedEvent(
        personality_id=personality_id,
        room_id=room.id,
        name=room.name,
        room_type=room.type,
    )
    await secure_pubsub.publish_personality_room_message(personality_id, update_event)

    return {"personality_room": room.model_dump()}


@blueprint.delete("/<uuid:personality_id>/rooms/<uuid:room_id>")
@requires_auth
@requires_csrf
async def delete_personality_room(personality_id: UUID, room_id: UUID) -> Response:
    """Delete a personality room.

    Args:
        personality_id: The ID of the personality
        room_id: The ID of the room to delete

    Returns:
        204 No Content

    Raises:
        NotFound: If room doesn't exist
        Forbidden: If user doesn't have admin access
    """
    user_id = request.token.user_id

    # Check personality access
    await check_personality_access(personality_id, user_id)

    # Check if user has admin access to the room
    has_admin = await PersonalityRoomModel.has_admin_access(room_id, user_id)
    if not has_admin:
        raise Forbidden("You do not have permission to delete this room")

    # Delete the room (cascade will handle room users and messages)
    deleted = await PersonalityRoomModel.delete(room_id)
    if not deleted:
        raise NotFound(f"Room with id {room_id} not found")

    # Broadcast room deletion event
    delete_event = PersonalityRoomDeletedEvent(
        personality_id=personality_id,
        room_id=room_id,
    )
    await secure_pubsub.publish_personality_room_message(personality_id, delete_event)

    return Response(status=204)


@blueprint.get("/<uuid:personality_id>/rooms/<uuid:room_id>/users")
@requires_auth
async def get_room_users(personality_id: UUID, room_id: UUID) -> dict[str, list[dict]]:
    """Get all users in a personality room.

    Args:
        personality_id: The ID of the personality
        room_id: The ID of the room

    Returns:
        A dictionary with a list of users and their roles

    Raises:
        NotFound: If room doesn't exist or user doesn't have access
    """
    user_id = request.token.user_id

    # Check personality access
    await check_personality_access(personality_id, user_id)

    # Check room access
    room = await PersonalityRoomModel.get_for_user(room_id, user_id, personality_id)
    if not room:
        raise NotFound(f"Room with id {room_id} not found or you don't have access")

    # Get room users
    room_users = await PersonalityRoomUserModel.get_room_users(room_id)
    user_ids = [ru.user_id for ru in room_users]

    # Add creator if not in list
    if room.created_by and room.created_by not in user_ids:
        user_ids.append(room.created_by)

    # Get user details
    users = await UserModel.get_by_ids(user_ids) if user_ids else []

    # Build response with roles
    result = []
    for user in users:
        user_data = user.model_dump()
        # Check if user is creator
        if user.id == room.created_by:
            user_data["role"] = "admin"
        else:
            # Find role from room_users
            for ru in room_users:
                if ru.user_id == user.id:
                    user_data["role"] = ru.role
                    break
        result.append(user_data)

    return {"users": result}


@blueprint.post("/<uuid:personality_id>/rooms/<uuid:room_id>/users")
@requires_auth
@requires_csrf
async def add_room_user(personality_id: UUID, room_id: UUID) -> dict[str, dict]:
    """Add a user to a personality room.

    Args:
        personality_id: The ID of the personality
        room_id: The ID of the room

    Returns:
        A dictionary with the user details

    Raises:
        NotFound: If room doesn't exist
        Forbidden: If user doesn't have admin access
        BadRequest: If user is already in the room
    """
    user_id = request.token.user_id

    # Check personality access
    await check_personality_access(personality_id, user_id)

    # Check if user has admin access to the room
    has_admin = await PersonalityRoomModel.has_admin_access(room_id, user_id)
    if not has_admin:
        raise Forbidden("You do not have permission to add users to this room")

    # Parse request body
    body = await request.get_json()
    payload = PersonalityRoomUserPayload(**body)

    # Check if target user exists
    target_user = await UserModel.get(user_id=payload.user_id)
    if not target_user:
        raise NotFound(f"User with id {payload.user_id} not found")

    # Check if user already has access to the room
    existing = await PersonalityRoomUserModel.get(room_id, payload.user_id)
    if existing:
        raise BadRequest("User is already a member of this room")

    # Check if user is the creator (already has access)
    room = await PersonalityRoomModel.get(room_id)
    if room and room.created_by == payload.user_id:
        raise BadRequest("User is the creator of this room")

    # Add user to room
    create_params = PersonalityRoomUserModel.CreateParams(
        personality_room_id=room_id,
        user_id=payload.user_id,
        role=payload.role,
    )
    room_user = await PersonalityRoomUserModel.create(params=create_params)

    # Broadcast user joined event
    join_event = UserJoinedPersonalityRoomEvent(
        personality_id=personality_id,
        room_id=room_id,
        user_id=payload.user_id,
        role=payload.role,
    )
    await secure_pubsub.publish_personality_room_message(personality_id, join_event)

    # Return user details with role
    user_data = target_user.model_dump()
    user_data["role"] = room_user.role

    return {"user": user_data}


@blueprint.delete("/<uuid:personality_id>/rooms/<uuid:room_id>/users/<user_id>")
@requires_auth
@requires_csrf
async def remove_room_user(
    personality_id: UUID, room_id: UUID, user_id: str
) -> Response:
    """Remove a user from a personality room.

    Args:
        personality_id: The ID of the personality
        room_id: The ID of the room
        user_id: The ID of the user to remove

    Returns:
        204 No Content

    Raises:
        NotFound: If room doesn't exist
        Forbidden: If user doesn't have permission
        BadRequest: If trying to remove the creator
    """
    requesting_user_id = request.token.user_id

    # Check personality access
    await check_personality_access(personality_id, requesting_user_id)

    # Get room details
    room = await PersonalityRoomModel.get(room_id)
    if not room:
        raise NotFound(f"Room with id {room_id} not found")

    # Check if trying to remove the creator
    if room.created_by == user_id:
        raise BadRequest("Cannot remove the room creator")

    # Check permissions: admin can remove anyone, users can remove themselves
    if requesting_user_id != user_id:
        has_admin = await PersonalityRoomModel.has_admin_access(
            room_id, requesting_user_id
        )
        if not has_admin:
            raise Forbidden("You do not have permission to remove other users")

    # Remove user from room
    await PersonalityRoomUserModel.delete(room_id, user_id)

    # Broadcast user left event
    leave_event = UserLeftPersonalityRoomEvent(
        personality_id=personality_id,
        room_id=room_id,
        user_id=user_id,
    )
    await secure_pubsub.publish_personality_room_message(personality_id, leave_event)

    return Response(status=204)
