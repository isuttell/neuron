from uuid import UUID

from pydantic import BaseModel, Field
from quart import Blueprint, Response
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from neuron_server.controllers.auth import requires_auth
from neuron_server.controllers.csrf import requires_csrf
from neuron_server.controllers.events.personality_room_events import (
    PersonalityRoomCreatedEvent,
    PersonalityRoomDataEvent,
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
    name: str | None = Field(description="The name of the room", default=None)
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

    # Build normalized response with separate arrays
    personality_room_users = []

    # Add all room users
    for ru in all_room_users:
        personality_room_users.append(
            {
                "user_id": ru.user_id,
                "personality_room_id": str(ru.personality_room_id),
                "role": ru.role,
            }
        )

    # Add creators as admins if not already in room users
    for room in rooms:
        if room.created_by:
            # Check if creator is already in room users
            creator_exists = any(
                ru.personality_room_id == room.id and ru.user_id == room.created_by
                for ru in all_room_users
            )
            if not creator_exists:
                personality_room_users.append(
                    {
                        "user_id": room.created_by,
                        "personality_room_id": str(room.id),
                        "role": "admin",
                    }
                )

    return {
        "personality_rooms": [room.model_dump() for room in rooms],
        "personality_room_users": personality_room_users,
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

    # Generate default name if not provided
    if payload.name is None:
        payload.name = "Chat Room"

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
    await secure_pubsub.publish_personality_room_message(
        personality_id, room.id, room_event
    )

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

    # Build normalized response
    personality_room_users = []

    # Add all room users
    for ru in room_users:
        personality_room_users.append(
            {
                "user_id": ru.user_id,
                "personality_room_id": str(ru.personality_room_id),
                "role": ru.role,
            }
        )

    # Add creator as admin if not already in room users
    if room.created_by:
        creator_exists = any(ru.user_id == room.created_by for ru in room_users)
        if not creator_exists:
            personality_room_users.append(
                {
                    "user_id": room.created_by,
                    "personality_room_id": str(room.id),
                    "role": "admin",
                }
            )

    return {
        "personality_room": room.model_dump(),
        "personality_room_users": personality_room_users,
        "users": [user.model_dump() for user in users],
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
    await secure_pubsub.publish_personality_room_message(
        personality_id, room.id, update_event
    )

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
    await secure_pubsub.publish_personality_room_message(
        personality_id, room_id, delete_event
    )

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

    # Build normalized response
    personality_room_users = []

    # Add all room users
    for ru in room_users:
        personality_room_users.append(
            {
                "user_id": ru.user_id,
                "personality_room_id": str(ru.personality_room_id),
                "role": ru.role,
            }
        )

    # Add creator as admin if not already in room users
    if room.created_by:
        creator_exists = any(ru.user_id == room.created_by for ru in room_users)
        if not creator_exists:
            personality_room_users.append(
                {
                    "user_id": room.created_by,
                    "personality_room_id": str(room_id),
                    "role": "admin",
                }
            )

    return {
        "users": [user.model_dump() for user in users],
        "personality_room_users": personality_room_users,
    }


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
    users = await UserModel.get_by_ids([payload.user_id])
    if not users:
        raise NotFound(f"User with id {payload.user_id} not found")
    target_user = users[0]

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
    await secure_pubsub.publish_personality_room_message(
        personality_id, room_id, join_event
    )

    # Send complete room data to the newly added user
    # Get room details
    room = await PersonalityRoomModel.get(room_id)
    if room:
        # Get all room users
        all_room_users = await PersonalityRoomUserModel.get_room_users(room_id)
        user_ids = [ru.user_id for ru in all_room_users]

        # Add creator if not in list
        if room.created_by and room.created_by not in user_ids:
            user_ids.append(room.created_by)

        # Get user details
        users = await UserModel.get_by_ids(user_ids) if user_ids else []

        # Build normalized room users data
        personality_room_users = []

        # Add all room users
        for ru in all_room_users:
            personality_room_users.append(
                {
                    "user_id": ru.user_id,
                    "personality_room_id": str(ru.personality_room_id),
                    "role": ru.role,
                }
            )

        # Add creator as admin if not already in room users
        if room.created_by:
            creator_exists = any(ru.user_id == room.created_by for ru in all_room_users)
            if not creator_exists:
                personality_room_users.append(
                    {
                        "user_id": room.created_by,
                        "personality_room_id": str(room_id),
                        "role": "admin",
                    }
                )

        # Create and send room data event to the newly added user
        room_data_event = PersonalityRoomDataEvent(
            personality_room=room.model_dump(),
            personality_room_users=personality_room_users,
            users=[user.model_dump() for user in users],
        )
        await secure_pubsub.publish_to_user(payload.user_id, room_data_event)

    # Return normalized response
    return {
        "user": target_user.model_dump(),
        "personality_room_user": {
            "user_id": room_user.user_id,
            "personality_room_id": str(room_user.personality_room_id),
            "role": room_user.role,
        },
    }


@blueprint.post("/<uuid:personality_id>/rooms/<uuid:room_id>/users/email")
@requires_auth
@requires_csrf
async def add_room_user_by_email(
    personality_id: UUID, room_id: UUID
) -> dict[str, dict]:
    """Add a user to a personality room by email.

    Args:
        personality_id: The ID of the personality
        room_id: The ID of the room

    Returns:
        A dictionary with the created room user and user details

    Raises:
        BadRequest: If email is missing or user already in room
        NotFound: If personality, room, or user not found
        Forbidden: If user doesn't have permission
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
    email = body.get("email")
    if not email:
        raise BadRequest("Email is required")

    # Find user by email
    user = await UserModel.get_by_email(email=email)
    if not user:
        raise BadRequest(f"No user found with email: {email}")

    # Check if user already has access to the room
    existing = await PersonalityRoomUserModel.get(room_id, user.id)
    if existing:
        raise BadRequest("User is already a member of this room")

    # Check if user is the creator (already has access)
    room = await PersonalityRoomModel.get(room_id)
    if room and room.created_by == user.id:
        raise BadRequest("User is the creator of this room")

    # Add user to room
    create_params = PersonalityRoomUserModel.CreateParams(
        personality_room_id=room_id,
        user_id=user.id,
        role=body.get("role", "user"),
    )
    room_user = await PersonalityRoomUserModel.create(params=create_params)

    # Broadcast user joined event
    join_event = UserJoinedPersonalityRoomEvent(
        personality_id=personality_id,
        room_id=room_id,
        user_id=user.id,
        role=room_user.role,
    )
    await secure_pubsub.publish_personality_room_message(
        personality_id, room_id, join_event
    )

    # Send complete room data to the newly added user
    # Get room details
    room_obj = await PersonalityRoomModel.get(room_id)
    if room_obj:
        # Get all room users
        all_room_users = await PersonalityRoomUserModel.get_room_users(room_id)
        user_ids = [ru.user_id for ru in all_room_users]

        # Add creator if not in list
        if room_obj.created_by and room_obj.created_by not in user_ids:
            user_ids.append(room_obj.created_by)

        # Get user details
        users = await UserModel.get_by_ids(user_ids) if user_ids else []

        # Build normalized room users data
        personality_room_users = []

        # Add all room users
        for ru in all_room_users:
            personality_room_users.append(
                {
                    "user_id": ru.user_id,
                    "personality_room_id": str(ru.personality_room_id),
                    "role": ru.role,
                }
            )

        # Add creator as admin if not already in room users
        if room_obj.created_by:
            creator_exists = any(
                ru.user_id == room_obj.created_by for ru in all_room_users
            )
            if not creator_exists:
                personality_room_users.append(
                    {
                        "user_id": room_obj.created_by,
                        "personality_room_id": str(room_id),
                        "role": "admin",
                    }
                )

        # Create and send room data event to the newly added user
        room_data_event = PersonalityRoomDataEvent(
            personality_room=room_obj.model_dump(),
            personality_room_users=personality_room_users,
            users=[u.model_dump() for u in users],
        )
        await secure_pubsub.publish_to_user(user.id, room_data_event)

    # Return normalized response
    return {
        "user": user.model_dump(),
        "personality_room_user": {
            "user_id": room_user.user_id,
            "personality_room_id": str(room_user.personality_room_id),
            "role": room_user.role,
        },
    }


@blueprint.put("/<uuid:personality_id>/rooms/<uuid:room_id>/users/<user_id>")
@requires_auth
@requires_csrf
async def update_room_user(
    personality_id: UUID, room_id: UUID, user_id: str
) -> dict[str, dict]:
    """Update a user's properties in a personality room.

    Args:
        personality_id: The ID of the personality
        room_id: The ID of the room
        user_id: The ID of the user to update

    Returns:
        A dictionary with the updated user details

    Raises:
        NotFound: If room or user doesn't exist
        Forbidden: If user doesn't have permission
        BadRequest: If invalid data provided
    """
    requesting_user_id = request.token.user_id

    # Check personality access
    await check_personality_access(personality_id, requesting_user_id)

    # Check if user has admin access to the room
    has_admin = await PersonalityRoomModel.has_admin_access(room_id, requesting_user_id)
    if not has_admin:
        raise Forbidden("You do not have permission to update users in this room")

    # Parse request body
    body = await request.get_json()

    # Currently only role can be updated
    if "role" in body:
        new_role = body["role"]
        if new_role not in ["admin", "user"]:
            raise BadRequest("Invalid role. Must be 'admin' or 'user'")

        # Update user role
        try:
            room_user = await PersonalityRoomUserModel.update_role(
                personality_room_id=room_id, user_id=user_id, role=new_role
            )
        except ValueError as err:
            raise NotFound("User not found in room") from err
    else:
        raise BadRequest("No fields to update")

    # Get updated user details
    users = await UserModel.get_by_ids([user_id])
    if not users:
        raise NotFound(f"User with id {user_id} not found")
    user = users[0]

    # Return normalized response
    return {
        "user": user.model_dump(),
        "personality_room_user": {
            "user_id": room_user.user_id,
            "personality_room_id": str(room_user.personality_room_id),
            "role": room_user.role,
        },
    }


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
    await secure_pubsub.publish_personality_room_message(
        personality_id, room_id, leave_event
    )

    return Response(status=204)
