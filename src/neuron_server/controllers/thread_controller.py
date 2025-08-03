import asyncio
from uuid import UUID

from pydantic import BaseModel
from quart import Blueprint, Response
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from neuron_server.controllers.auth import requires_auth
from neuron_server.controllers.csrf import requires_csrf
from neuron_server.controllers.events.thread_events import CancelRequestEvent
from neuron_server.controllers.message_controller import process_message_request
from neuron_server.decorators import rate_limit
from neuron_server.event_router import EventRouter
from neuron_server.llms import agent
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.models.personality_room_model import PersonalityRoomModel
from neuron_server.models.personality_room_user_model import PersonalityRoomUserModel
from neuron_server.models.thread_model import ThreadModel
from neuron_server.models.thread_user_model import ThreadUserModel
from neuron_server.models.user_model import UserModel
from neuron_server.secure_pubsub import secure_pubsub
from neuron_server.type_defs.request_proxy import request

blueprint = Blueprint("thread", __name__)
router = EventRouter()

# Thread limits for performance
DEFAULT_THREAD_LIMIT = 50
MAX_THREAD_LIMIT = 500


class UpdateThread(BaseModel):
    name: str
    context: str
    memory: str
    status: str


class ThreadUserPayload(BaseModel):
    user_id: str
    role: str = "user"


async def check_thread_access(thread_id: UUID, user_id: str) -> ThreadModel:
    """Check if a user has access to a thread.

    Args:
        thread_id: The ID of the thread to check
        user_id: The ID of the user to check

    Returns:
        The thread if the user has access

    Raises:
        NotFound: If the thread doesn't exist
        Forbidden: If the user doesn't have access to the thread
    """
    thread = await ThreadModel.get(thread_id=thread_id)
    if not thread:
        raise NotFound("Thread not found")

    # Check if user is in thread_users
    thread_user = await ThreadUserModel.get(thread_id=thread_id, user_id=user_id)
    if not thread_user:
        raise Forbidden("You don't have access to this thread")

    return thread


@blueprint.get("/<uuid:thread_id>")
@requires_auth
async def get_thread(thread_id: UUID) -> dict[str, list[dict]]:
    thread = await check_thread_access(
        thread_id=thread_id, user_id=request.token.user_id
    )

    # Get thread users
    thread_users = await ThreadUserModel.get_thread_users(thread_id=thread_id)

    return {
        "threads": [thread.model_dump()],
        "thread_users": [
            {"user_id": tu.user_id, "thread_id": str(tu.thread_id), "role": tu.role}
            for tu in thread_users
        ],
    }


@blueprint.get("/personality/<uuid:personality_id>")
@requires_auth
async def get_threads(personality_id: UUID) -> dict[str, list[dict]]:
    # Get optional limit parameter from query string
    limit = request.args.get("limit", default=DEFAULT_THREAD_LIMIT, type=int)

    # Validate limit parameter
    if limit < 1 or limit > MAX_THREAD_LIMIT:
        raise BadRequest(f"Limit must be between 1 and {MAX_THREAD_LIMIT}")

    # Get threads the user has access to via thread_users
    thread_users = await ThreadUserModel.get_user_threads(user_id=request.token.user_id)
    thread_ids = [tu.thread_id for tu in thread_users]

    # Get threads efficiently using bulk query with WHERE IN
    threads = []
    if thread_ids:
        threads = await ThreadModel.get_by_ids(
            thread_ids=thread_ids, personality_id=personality_id, limit=limit
        )

    # Sort all threads by updated_at DESC (already sorted by get_by_ids)
    sorted_threads = threads

    # Get thread_users for all final threads efficiently with bulk query
    final_thread_ids = [t.id for t in sorted_threads]
    all_thread_users = []

    if final_thread_ids:
        # Bulk fetch thread users for all threads in a single query
        bulk_thread_users = await ThreadUserModel.get_bulk_thread_users(
            final_thread_ids
        )

        # Group thread users by thread_id for easier processing
        thread_users_by_thread = {}
        for tu in bulk_thread_users:
            if tu.thread_id not in thread_users_by_thread:
                thread_users_by_thread[tu.thread_id] = []
            thread_users_by_thread[tu.thread_id].append(tu)

        # Process each thread to add thread users
        for thread in sorted_threads:
            thread_users_for_thread = thread_users_by_thread.get(thread.id, [])

            # Add all thread users
            for tu in thread_users_for_thread:
                all_thread_users.append(
                    {
                        "user_id": tu.user_id,
                        "thread_id": str(tu.thread_id),
                        "role": tu.role,
                    }
                )

    return {
        "threads": [thread.model_dump() for thread in sorted_threads],
        "thread_users": all_thread_users,
    }


@blueprint.post("/")
@requires_auth
@requires_csrf
@rate_limit()
async def post_create_thread() -> dict[str, dict]:
    files = await request.files
    form = await request.form
    personality_id = form.get("personality_id")
    if not personality_id:
        raise BadRequest("personality_id is required")

    personality = await PersonalityModel.get(personality_id=UUID(personality_id))
    if not personality:
        raise BadRequest("Personality not found")

    # Create thread
    create_params = ThreadModel.CreateParams(
        personality_id=personality.id,
        user_id=request.token.user_id,
        name=form.get("name", ""),
        context=form.get("context", ""),
        memory=form.get("memory", ""),
        status="idle",
    )
    thread = await ThreadModel.create(params=create_params)

    # Add thread creator as admin in thread_users
    thread_user_params = ThreadUserModel.CreateParams(
        thread_id=thread.id,
        user_id=request.token.user_id,
        role="admin",
    )
    await ThreadUserModel.create(params=thread_user_params)

    # Check if we should start with a greeting
    greeting = str(form.get("greeting", "false")).lower() == "true"
    prompt: str | None = None
    if greeting:
        prompt = (
            "<|AI|>\nStart the conversation in a sentence or two and then "
            "provide some prompt suggestions as a list. Don't run any tools\n<|AI|>"
        )
    else:
        prompt = await process_message_request(files, form)

    if prompt and len(prompt.strip()) > 0:
        # Start the conversation and stream the response in the background
        asyncio.create_task(
            agent.astream(
                {
                    "thread_id": thread.id,
                    "personality_id": personality.id,
                    "user_id": request.token.user_id,
                    "username": request.token.nickname,
                    "prompt": prompt,
                }
            )
        )
        thread.message_count = 1
        await thread.save()

    return {"thread": thread.model_dump()}


@blueprint.delete("/<uuid:thread_id>")
@requires_auth
@requires_csrf
async def delete_thread(thread_id: UUID) -> Response:
    thread = await ThreadModel.get(thread_id=thread_id)
    if not thread:
        raise NotFound("Thread not found")

    # Only thread admins can delete it
    thread_user = await ThreadUserModel.get(
        thread_id=thread_id, user_id=request.token.user_id
    )
    if not thread_user or thread_user.role != "admin":
        raise Forbidden("Only thread admins can delete threads")

    await ThreadModel.delete(thread_id=thread_id)
    return Response(status=204)


@blueprint.put("/<uuid:thread_id>")
@requires_auth
@requires_csrf
async def update_thread(thread_id: UUID) -> dict[str, list[dict]]:
    body = await request.get_json()
    payload = UpdateThread(**body)

    # Check if user has access to the thread
    thread = await check_thread_access(
        thread_id=thread_id, user_id=request.token.user_id
    )

    # Only thread admins can update it
    thread_user = await ThreadUserModel.get(
        thread_id=thread_id, user_id=request.token.user_id
    )
    if not thread_user or thread_user.role != "admin":
        raise Forbidden("Only thread admins can update threads")

    update_params = ThreadModel.UpdateParams(
        thread_id=thread_id,
        name=payload.name,
        context=payload.context,
        memory=payload.memory,
        status=payload.status,
        message_count=thread.message_count,
    )
    thread = await ThreadModel.update(params=update_params)
    return {"threads": [thread.model_dump()]}


@blueprint.get("/<uuid:thread_id>/users")
@requires_auth
async def get_thread_users(thread_id: UUID) -> dict[str, list[dict]]:
    """Get all users associated with a thread.

    Returns:
        A dictionary with a list of user objects
    """
    # Check if user has access to the thread
    await check_thread_access(thread_id=thread_id, user_id=request.token.user_id)

    # Get thread users
    thread_users = await ThreadUserModel.get_thread_users(thread_id=thread_id)

    # Get user details
    user_ids = [tu.user_id for tu in thread_users]
    users = await UserModel.get_by_ids(user_ids=user_ids)

    # Add role to each user
    result = []
    for user in users:
        user_dict = user.model_dump()
        # Find role from thread_users
        for tu in thread_users:
            if tu.user_id == user.id:
                user_dict["role"] = tu.role
                break

        result.append(user_dict)

    return {"users": result}


@blueprint.post("/<uuid:thread_id>/users")
@requires_auth
@requires_csrf
async def add_thread_user(thread_id: UUID) -> dict[str, dict]:
    """Add a user to a thread.

    Returns:
        A dictionary with the created thread user
    """
    body = await request.get_json()
    payload = ThreadUserPayload(**body)

    # Get the thread
    thread = await ThreadModel.get(thread_id=thread_id)
    if not thread:
        raise NotFound("Thread not found")

    # Only thread admins can add users
    thread_user = await ThreadUserModel.get(
        thread_id=thread_id, user_id=request.token.user_id
    )
    if not thread_user or thread_user.role != "admin":
        raise Forbidden("Only thread admins can add users")

    # Check if user exists
    users = await UserModel.get_by_ids(user_ids=[payload.user_id])
    if not users:
        raise BadRequest("User not found")

    # Check if user is already in the thread
    existing = await ThreadUserModel.get(thread_id=thread_id, user_id=payload.user_id)
    if existing:
        raise BadRequest("User is already in the thread")

    # Add user to thread
    create_params = ThreadUserModel.CreateParams(
        thread_id=thread_id,
        user_id=payload.user_id,
        role=payload.role,
    )
    thread_user = await ThreadUserModel.create(params=create_params)

    return {"thread_user": thread_user.model_dump()}


@blueprint.post("/<uuid:thread_id>/users/email")
@requires_auth
@requires_csrf
async def add_thread_user_by_email(thread_id: UUID) -> dict[str, dict]:
    """Add a user to a thread by email.

    Returns:
        A dictionary with the created thread user and user details
    """
    body = await request.get_json()
    email = body.get("email")
    if not email:
        raise BadRequest("Email is required")

    # Get the thread
    thread = await ThreadModel.get(thread_id=thread_id)
    if not thread:
        raise NotFound("Thread not found")

    # Only thread admins can add users
    thread_user = await ThreadUserModel.get(
        thread_id=thread_id, user_id=request.token.user_id
    )
    if not thread_user or thread_user.role != "admin":
        raise Forbidden("Only thread admins can add users")

    # Find user by email
    user = await UserModel.get_by_email(email=email)
    if not user:
        raise BadRequest(f"No user found with email: {email}")

    # Check if user is already in the thread
    existing = await ThreadUserModel.get(thread_id=thread_id, user_id=user.id)
    if existing:
        raise BadRequest("User is already in the thread")

    # Add user to thread
    create_params = ThreadUserModel.CreateParams(
        thread_id=thread_id,
        user_id=user.id,
        role="user",  # Default role is user
    )
    thread_user = await ThreadUserModel.create(params=create_params)

    return {
        "thread_user": thread_user.model_dump(),
        "user": user.model_dump(),
    }


@blueprint.delete("/<uuid:thread_id>/users/<string:user_id>")
@requires_auth
@requires_csrf
async def remove_thread_user(thread_id: UUID, user_id: str) -> Response:
    """Remove a user from a thread.

    Returns:
        204 No Content
    """
    # Get the thread
    thread = await ThreadModel.get(thread_id=thread_id)
    if not thread:
        raise NotFound("Thread not found")

    # Users can remove themselves
    if user_id == request.token.user_id:
        await ThreadUserModel.delete(thread_id=thread_id, user_id=user_id)
        return Response(status=204)

    # Only thread admins can remove other users
    thread_user = await ThreadUserModel.get(
        thread_id=thread_id, user_id=request.token.user_id
    )
    if not thread_user or thread_user.role != "admin":
        raise Forbidden("Only thread admins can remove users")

    # Remove user from thread
    await ThreadUserModel.delete(thread_id=thread_id, user_id=user_id)

    return Response(status=204)


@blueprint.put("/<uuid:thread_id>/users/<string:user_id>")
@requires_auth
@requires_csrf
async def update_thread_user(thread_id: UUID, user_id: str) -> dict[str, dict]:
    """Update a user's role in a thread.

    Returns:
        A dictionary with the updated thread user
    """
    body = await request.get_json()
    payload = ThreadUserPayload(**body)

    # Get the thread
    thread = await ThreadModel.get(thread_id=thread_id)
    if not thread:
        raise NotFound("Thread not found")

    # Only thread admins can update roles
    thread_user = await ThreadUserModel.get(
        thread_id=thread_id, user_id=request.token.user_id
    )
    if not thread_user or thread_user.role != "admin":
        raise Forbidden("Only thread admins can update roles")

    # Update user role
    try:
        thread_user = await ThreadUserModel.update_role(
            thread_id=thread_id, user_id=user_id, role=payload.role
        )
    except ValueError as err:
        raise NotFound("User not found in thread") from err

    return {"thread_user": thread_user.model_dump()}


@blueprint.post("/<uuid:thread_id>/cancel")
@requires_auth
@requires_csrf
async def cancel_thread(thread_id: UUID) -> Response:
    """Cancel a running agent task for a thread.

    Returns:
        204 No Content
    """
    # Check if user has access to the thread
    await check_thread_access(thread_id=thread_id, user_id=request.token.user_id)

    # Publish cancellation event to users with access to the thread
    await secure_pubsub.publish_thread_cancellation(
        CancelRequestEvent(thread_id=thread_id)
    )

    return Response(status=204)


async def _get_user_threads_and_rooms(
    user_id: str, limit: int
) -> tuple[list, list, list]:
    """Get threads and rooms for a user."""
    # Get all threads the user has access to via thread_users
    thread_users = await ThreadUserModel.get_user_threads(user_id=user_id)
    thread_ids = [tu.thread_id for tu in thread_users]

    # Get threads efficiently using bulk query
    threads = []
    if thread_ids:
        # Get more items to allow for combined sorting
        threads = await ThreadModel.get_by_ids(thread_ids=thread_ids, limit=limit * 2)

    # Get all personalities the user has access to and get their rooms
    personalities = await PersonalityModel.list_for_user(user_id=user_id)
    personality_ids = [p.id for p in personalities]

    all_rooms = []
    all_room_users = []

    # Get rooms for each personality that the user has access to
    for personality_id in personality_ids:
        rooms = await PersonalityRoomModel.list_for_personality(personality_id, user_id)
        all_rooms.extend(rooms)

        # Get room users for these rooms
        room_ids = [room.id for room in rooms]
        if room_ids:
            room_users = await PersonalityRoomUserModel.get_bulk_room_users(room_ids)
            all_room_users.extend(room_users)

    return threads, all_rooms, all_room_users


async def _combine_and_sort_items(threads: list, rooms: list, limit: int) -> list[dict]:
    """Combine threads and rooms, sort by updated_at, and return top items."""
    combined_items = []

    # Add threads with type identifier
    for thread in threads:
        combined_items.append(
            {"type": "thread", "item": thread, "updated_at": thread.updated_at}
        )

    # Add rooms with type identifier
    for room in rooms:
        combined_items.append(
            {"type": "room", "item": room, "updated_at": room.updated_at}
        )

    # Sort by updated_at descending and take top items
    combined_items.sort(key=lambda x: x["updated_at"], reverse=True)
    return combined_items[:limit]


async def _get_users_for_items(
    final_threads: list, final_rooms: list, bulk_room_users: list
) -> tuple[list[dict], list[dict], list]:
    """Get user data for threads and rooms."""
    final_thread_ids = [t.id for t in final_threads]
    final_thread_users = []

    if final_thread_ids:
        bulk_thread_users = await ThreadUserModel.get_bulk_thread_users(
            final_thread_ids
        )
        for tu in bulk_thread_users:
            final_thread_users.append(
                {
                    "user_id": tu.user_id,
                    "thread_id": str(tu.thread_id),
                    "role": tu.role,
                }
            )

    final_room_ids = [r.id for r in final_rooms]
    final_room_users = []

    if final_room_ids:
        for ru in bulk_room_users:
            final_room_users.append(
                {
                    "user_id": ru.user_id,
                    "personality_room_id": str(ru.personality_room_id),
                    "role": ru.role,
                }
            )

        # Add room creators as admins if not already in room users
        for room in final_rooms:
            if room.created_by:
                creator_exists = any(
                    ru.personality_room_id == room.id and ru.user_id == room.created_by
                    for ru in bulk_room_users
                )
                if not creator_exists:
                    final_room_users.append(
                        {
                            "user_id": room.created_by,
                            "personality_room_id": str(room.id),
                            "role": "admin",
                        }
                    )

    # Get all unique user IDs for user data
    user_ids = set()
    if final_thread_ids:
        user_ids.update(tu.user_id for tu in bulk_thread_users)
    if final_room_ids:
        user_ids.update(ru.user_id for ru in bulk_room_users)
        user_ids.update(room.created_by for room in final_rooms if room.created_by)

    # Get user details
    users = await UserModel.get_by_ids(list(user_ids)) if user_ids else []

    return final_thread_users, final_room_users, users


@blueprint.get("/recent-combined")
@requires_auth
async def get_recent_combined() -> dict[str, list[dict]]:
    """Get recent threads and personality rooms across all personalities.

    Returns:
        A dictionary with threads, thread_users, personality_rooms,
        personality_room_users, and users
    """
    user_id = request.token.user_id
    limit = request.args.get("limit", default=DEFAULT_THREAD_LIMIT, type=int)

    # Validate limit parameter
    if limit < 1 or limit > MAX_THREAD_LIMIT:
        raise BadRequest(f"Limit must be between 1 and {MAX_THREAD_LIMIT}")

    # Get threads and rooms for the user
    threads, all_rooms, all_room_users = await _get_user_threads_and_rooms(
        user_id, limit
    )

    # Combine and sort items
    combined_items = await _combine_and_sort_items(threads, all_rooms, limit)

    # Extract the final threads and rooms
    final_threads = [
        item["item"] for item in combined_items if item["type"] == "thread"
    ]
    final_rooms = [item["item"] for item in combined_items if item["type"] == "room"]

    # Get users for the final items
    final_thread_users, final_room_users, users = await _get_users_for_items(
        final_threads, final_rooms, all_room_users
    )

    return {
        "threads": [thread.model_dump() for thread in final_threads],
        "thread_users": final_thread_users,
        "personality_rooms": [room.model_dump() for room in final_rooms],
        "personality_room_users": final_room_users,
        "users": [user.model_dump() for user in users],
    }
