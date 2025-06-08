import asyncio
from uuid import UUID

from pydantic import BaseModel
from quart import Blueprint, Response
from werkzeug.exceptions import BadRequest, Forbidden, NotFound

from neuron_server.controllers.auth import requires_auth
from neuron_server.controllers.csrf import requires_csrf
from neuron_server.controllers.message_controller import process_message_request
from neuron_server.decorators import rate_limit
from neuron_server.event_router import EventRouter
from neuron_server.llms import agent
from neuron_server.models.personality_model import PersonalityModel
from neuron_server.models.thread_model import ThreadModel
from neuron_server.models.thread_user_model import ThreadUserModel
from neuron_server.models.user_model import UserModel
from neuron_server.type_defs.request_proxy import request

blueprint = Blueprint("thread", __name__)
router = EventRouter()


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

    # Thread owner always has access
    if thread.user_id == user_id:
        return thread

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
    return {"threads": [thread.model_dump()]}


@blueprint.get("/personality/<uuid:personality_id>")
@requires_auth
async def get_threads(personality_id: UUID) -> dict[str, list[dict]]:
    # Get threads owned by the user
    owned_threads = await ThreadModel.list(
        personality_id=personality_id, user_id=request.token.user_id
    )

    # Get threads the user has access to via thread_users
    thread_users = await ThreadUserModel.get_user_threads(user_id=request.token.user_id)
    thread_ids = [tu.thread_id for tu in thread_users]

    # Filter thread_users by personality_id
    if thread_ids:
        shared_threads = []
        for thread_id in thread_ids:
            thread = await ThreadModel.get(thread_id=thread_id)
            if thread and thread.personality_id == personality_id:
                shared_threads.append(thread)
    else:
        shared_threads = []

    # Combine and deduplicate threads
    all_threads = {thread.id: thread for thread in owned_threads}
    for thread in shared_threads:
        if thread.id not in all_threads:
            all_threads[thread.id] = thread

    return {"threads": [thread.model_dump() for thread in all_threads.values()]}


@blueprint.get("/recent")
@requires_auth
async def get_recent_threads() -> dict[str, list[dict]]:
    threads = await ThreadModel.get_recent_threads(
        hours=24, user_id=request.token.user_id
    )
    personality_ids = {thread.personality_id for thread in threads}
    personalities = await PersonalityModel.get_many(list(personality_ids))
    return {
        "threads": [thread.model_dump() for thread in threads],
        "personalities": [personality.model_dump() for personality in personalities],
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

    # Only the thread owner can delete it
    if thread.user_id != request.token.user_id:
        raise Forbidden("Only the thread owner can delete it")

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

    # Only the thread owner can update it
    if thread.user_id != request.token.user_id:
        raise Forbidden("Only the thread owner can update the thread")

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

    # Add thread owner
    thread = await ThreadModel.get(thread_id=thread_id)
    if thread:
        owner_users = await UserModel.get_by_ids(user_ids=[thread.user_id])
        if owner_users:
            owner = owner_users[0].model_dump()
            owner["role"] = "admin"  # Thread owner is always admin

            # Check if owner is already in the list
            existing_user_ids = [user["id"] for user in [u.model_dump() for u in users]]
            if thread.user_id not in existing_user_ids:
                users.append(owner_users[0])

    # Add role to each user
    result = []
    for user in users:
        user_dict = user.model_dump()
        # Find role from thread_users
        for tu in thread_users:
            if tu.user_id == user.id:
                user_dict["role"] = tu.role
                break
        else:
            # If not found in thread_users, must be the owner
            if user.id == thread.user_id:
                user_dict["role"] = "admin"

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

    # Only the thread owner or admins can add users
    if thread.user_id != request.token.user_id:
        # Check if the current user is an admin
        thread_user = await ThreadUserModel.get(
            thread_id=thread_id, user_id=request.token.user_id
        )
        if not thread_user or thread_user.role != "admin":
            raise Forbidden("Only thread owner or admins can add users")

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

    # Only the thread owner or admins can add users
    if thread.user_id != request.token.user_id:
        # Check if the current user is an admin
        thread_user = await ThreadUserModel.get(
            thread_id=thread_id, user_id=request.token.user_id
        )
        if not thread_user or thread_user.role != "admin":
            raise Forbidden("Only thread owner or admins can add users")

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

    # Only the thread owner or admins can remove other users
    if thread.user_id != request.token.user_id:
        # Check if the current user is an admin
        thread_user = await ThreadUserModel.get(
            thread_id=thread_id, user_id=request.token.user_id
        )
        if not thread_user or thread_user.role != "admin":
            raise Forbidden("Only thread owner or admins can remove users")

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

    # Only the thread owner or admins can update roles
    if thread.user_id != request.token.user_id:
        # Check if the current user is an admin
        thread_user = await ThreadUserModel.get(
            thread_id=thread_id, user_id=request.token.user_id
        )
        if not thread_user or thread_user.role != "admin":
            raise Forbidden("Only thread owner or admins can update roles")

    # Update user role
    try:
        thread_user = await ThreadUserModel.update_role(
            thread_id=thread_id, user_id=user_id, role=payload.role
        )
    except ValueError as err:
        raise NotFound("User not found in thread") from err

    return {"thread_user": thread_user.model_dump()}
