from quart import Blueprint, request
from neuron_server.event_router import EventRouter
from neuron_server.models import ThreadModel, MediaItemModel
from neuron_server.controllers.events.message_events import (
    PostMessage,
    CancelMessage,
)
from neuron_server.controllers.events.message_events import (
    ThreadMessage,
)
from uuid import UUID
from neuron_server.llms.agent import aget_state
from werkzeug.exceptions import NotFound, BadRequest
import neuron_server.llms.agent as agent
from neuron_server.pubsub import pubsub
from neuron_server.controllers.auth import requires_auth
from neuron_server.models.media_item_model import MediaItemModel
from neuron_server.util.file_utilities import process_uploaded_file

router = EventRouter()

blueprint = Blueprint("message", __name__)


@blueprint.get("/thread/<uuid:thread_id>")
@requires_auth
async def get_thread_messages(thread_id: UUID):
    thread = await ThreadModel.get(thread_id)
    if not thread:
        raise NotFound("Thread not found")

    state = await aget_state(thread_id=thread.id)
    messages = [
        ThreadMessage(**message.model_dump(), thread_id=thread.id)
        for message in (state.values.get("messages", []))
        if message.type != "system"
    ]

    # Get media items for this thread
    media_items = await MediaItemModel.get_thread_media(
        thread_id=thread.id, user_id=request.token.user_id
    )

    return {
        "threads": [thread.model_dump()],
        "messages": [message.model_dump() for message in messages],
        "media": [item.model_dump() for item in media_items],
    }


def format_ai_uploaded_file(filename: str, ext: str, url: str) -> str:
    # inform the agent that the user has uploaded a file
    if ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]:
        url = f"<image>![{filename}]({url})</image>"
    elif ext in [".mp3", ".wav", ".ogg", ".flac"]:
        url = f'<audio src="{url}"></audio>'
    elif ext in [".mp4", ".mov", ".avi", ".mkv"]:
        url = f'<video src="{url}"></video>'
    else:
        url = f"<{url}>"
    return f"<|AI|>The user has uploaded a file called '{filename}' to {url} as part the request<|AI|>"


@blueprint.post("/thread/<uuid:thread_id>")
@requires_auth
async def post_thread_message(thread_id: UUID):
    thread = await ThreadModel.get(thread_id)
    if not thread:
        raise NotFound("Thread not found")
    files = await request.files
    form = await request.form
    personality_id = form.get("personality_id")
    if not personality_id:
        raise BadRequest("personality_id is required")
    prompt = form.get("prompt")
    if not prompt:
        raise BadRequest("prompt is required")

    if "file" in files:
        filename, ext, url = await process_uploaded_file(files["file"])
        prompt = f"{format_ai_uploaded_file(filename, ext, url)}\n{prompt}"

    await agent.astream(
        thread_id=thread.id,
        personality_id=personality_id,
        user_id=request.token.user_id,
        username=request.token.nickname,
        prompt=prompt,
    )

    return {
        "status": "success",
    }, 201


@router.on(PostMessage)
async def apost_message(event: PostMessage) -> None:
    await agent.astream(
        thread_id=event.thread_id,
        personality_id=event.personality_id,
        user_id=None,
        prompt=event.prompt,
    )


@router.on(CancelMessage)
async def acancel_message(event: CancelMessage) -> None:
    await pubsub.publish(
        "cancel",
        event.thread_id,
    )
